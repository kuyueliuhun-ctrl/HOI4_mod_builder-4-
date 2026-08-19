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


class AtomicWriteTest(unittest.TestCase):
    """write_utils.atomic_write_text 原子写契约。"""

    def setUp(self):
        self.tmp = _mkdtemp("dsh_contract_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        from undo_mgr import get_undo_manager
        get_undo_manager().clear()

    def _path(self, name):
        return os.path.join(self.tmp, name)

    def test_write_new_file(self):
        from write_utils import atomic_write_text
        p = self._path("a/b/c.txt")
        atomic_write_text(p, "hello\n")
        with open(p, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "hello\n")

    def test_overwrite_no_tmp_left(self):
        from write_utils import atomic_write_text
        p = self._path("x.txt")
        atomic_write_text(p, "v1")
        atomic_write_text(p, "v2")
        with open(p, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "v2")
        leftovers = [n for n in os.listdir(self.tmp)
                     if n.startswith(".dsh_write_")]
        self.assertEqual(leftovers, [], "原子写不应残留临时文件")

    def test_bom_rejected_and_file_untouched(self):
        from write_utils import atomic_write_text, WriteContractError
        p = self._path("bom.txt")
        atomic_write_text(p, "original")
        with self.assertRaises(WriteContractError):
            atomic_write_text(p, "\ufeffbom content")
        with open(p, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "original", "BOM 拒绝后原文件必须保持不变")

    def test_unencodable_rejected_and_file_untouched(self):
        from write_utils import atomic_write_text, WriteContractError
        p = self._path("bad.txt")
        atomic_write_text(p, "original")
        with self.assertRaises(WriteContractError):
            atomic_write_text(p, "bad \ud800 char")
        with open(p, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "original")

    def test_allow_bom_flag(self):
        from write_utils import atomic_write_text
        p = self._path("loc.yml")
        atomic_write_text(p, "\ufeffl_simp_chinese:\n",
                          encoding="utf-8-sig", allow_bom=True)
        with open(p, "rb") as f:
            self.assertTrue(f.read().startswith(b"\xef\xbb\xbf"),
                            "utf-8-sig 应写入 BOM")

    def test_non_str_rejected(self):
        from write_utils import atomic_write_text, WriteContractError
        with self.assertRaises(WriteContractError):
            atomic_write_text(self._path("n.txt"), None)

    def test_undo_snapshot_restores_previous(self):
        from write_utils import atomic_write_text
        from undo_mgr import get_undo_manager
        p = self._path("u.txt")
        atomic_write_text(p, "old content")
        atomic_write_text(p, "new content")
        mgr = get_undo_manager()
        self.assertTrue(mgr.can_undo())
        path, ok = mgr.undo()
        self.assertTrue(ok)
        with open(p, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "old content")

    def test_write_failure_keeps_original(self):
        """写入失败时：原文件不被破坏（POSIX 只读目录模拟，Windows/root 跳过）。"""
        if os.name == "nt":
            self.skipTest("Windows 目录只读位不生效，权限模型不同")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root 无视目录权限位，无法模拟只读目录")
        from write_utils import atomic_write_text
        p = self._path("ro.txt")
        atomic_write_text(p, "keep me")
        ro_dir = self._path("ro_dir")
        os.makedirs(ro_dir)
        target = os.path.join(ro_dir, "inner.txt")
        try:
            os.chmod(ro_dir, 0o500)
        except OSError:
            self.skipTest("无法设置只读目录")
        try:
            atomic_write_text(target, "x")
            self.fail("只读目录写入应失败")
        except OSError:
            pass
        finally:
            try:
                os.chmod(ro_dir, 0o700)
            except OSError:
                pass
        self.assertTrue(os.path.isfile(p))
        with open(p, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "keep me")


class HealthCheckTest(unittest.TestCase):
    """export_health 导出前健康检查契约。"""

    def setUp(self):
        self.tmp = _mkdtemp("dsh_health_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, rel, content, mode="w"):
        fp = os.path.join(self.tmp, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, mode, encoding="utf-8", newline="") as f:
            f.write(content)
        return fp

    def _check(self):
        from export_health import run_export_health_check
        return run_export_health_check(self.tmp)

    def _sev(self, report, severity, category=None):
        return [i for i in report.issues
                if i.severity == severity
                and (category is None or i.category == category)]

    def test_clean_mod_no_errors(self):
        self._write("descriptor.mod", 'name = "Test"\npath = "test"\n')
        os.makedirs(os.path.join(self.tmp, "test"), exist_ok=True)
        self._write("common/national_focus/test.txt",
                    "focus_tree = {\n\tcountry = {\n\t\tfocus = {\n\t\t\tid = A_1\n\t\t}\n\t}\n}\n")
        report = self._check()
        self.assertEqual(report.counts["error"], 0,
                         "干净 mod 不应有 error：%s" % [i.message for i in report.issues])

    def test_missing_descriptor_is_error(self):
        report = self._check()
        self.assertTrue(self._sev(report, "error", "descriptor"))

    def test_unbalanced_braces_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("common/national_focus/bad.txt",
                    "focus_tree = {\n\tcountry = {\n\t\tfocus = {\n\t\t\tid = A\n")
        report = self._check()
        self.assertTrue(self._sev(report, "error", "syntax"))

    def test_bom_warning(self):
        self._write("descriptor.mod", 'name = "T"\n')
        with open(os.path.join(self.tmp, "bom.txt"), "wb") as f:
            f.write(b"\xef\xbb\xbfcontent")
        report = self._check()
        self.assertTrue(self._sev(report, "warning", "encoding"))

    def test_gfx_texture_missing_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("interface/test.gfx",
                    'spriteTypes = {\n\tspriteType = {\n\t\tname = "GFX_test"\n'
                    '\t\ttexturefile = "gfx/interface/missing.png"\n\t}\n}\n')
        report = self._check()
        self.assertTrue(self._sev(report, "error", "reference"))

    def test_gfx_texture_present_passes(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("gfx/interface/ok.png", "not-really-png")
        self._write("interface/test.gfx",
                    'spriteTypes = {\n\tspriteType = {\n\t\tname = "GFX_test"\n'
                    '\t\ttexturefile = "gfx/interface/ok.png"\n\t}\n}\n')
        report = self._check()
        self.assertEqual(self._sev(report, "error", "reference"), [])

    def test_duplicate_focus_id_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("common/national_focus/dup.txt",
                    "focus_tree = {\n\tcountry = {\n\t\tfocus = {\n\t\t\tid = DUP_A\n\t\t}\n"
                    "\t\tfocus = {\n\t\t\tid = DUP_A\n\t\t}\n\t}\n}\n")
        report = self._check()
        self.assertTrue(self._sev(report, "error", "duplicate"))

    def test_duplicate_tech_id_is_error(self):
        self._write("descriptor.mod", 'name = "T"\n')
        self._write("common/technologies/dup.txt",
                    "technologies = {\n\ttech1 = {\n\t}\n\ttech1 = {\n\t}\n}\n")
        report = self._check()
        self.assertTrue(self._sev(report, "error", "duplicate"))


class WriteDisciplineScannerTest(unittest.TestCase):
    """tools/check_write_discipline.py 静态扫描契约。"""

    def setUp(self):
        self.tmp = _mkdtemp("dsh_discipline_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, rel, content):
        fp = os.path.join(self.tmp, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

    def test_detects_direct_text_write(self):
        self._write("bad_mod.py",
                    "import os\n"
                    "def save(path, text):\n"
                    "    with open(path, 'w', encoding='utf-8') as f:\n"
                    "        f.write(text)\n")
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        try:
            from check_write_discipline import scan_root
            violations, _reg, _bin, _checked = scan_root(self.tmp)
        finally:
            sys.path.remove(os.path.join(PROJECT_ROOT, "tools"))
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][1], 3)  # open 调用所在行

    def test_binary_copy_is_not_violation(self):
        self._write("ok_mod.py",
                    "import shutil\n"
                    "shutil.copyfile('a.png', 'b.png')\n")
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        try:
            from check_write_discipline import scan_root
            violations, _reg, binaries, _checked = scan_root(self.tmp)
        finally:
            sys.path.remove(os.path.join(PROJECT_ROOT, "tools"))
        self.assertEqual(violations, [])
        self.assertEqual(len(binaries), 1)


class RegionOpsTest(unittest.TestCase):
    """map_region_ops 区域解析/写回契约。"""

    STRAT_FILE = (
        "strategic_region = {\n"
        "\tid = 101\n"
        "\tname = STRATEGICREGION_101\n"
        "\tprovinces = {\n"
        "\t\t1 2 3\n"
        "\t}\n"
        "}\n"
        "strategic_region = {\n"
        "\tid = 102\n"
        "\tprovinces = { 4 5 }\n"
        "}\n"
    )

    def _parse(self, kind="strategic_region"):
        from map_region_ops import parse_region_file
        return parse_region_file(self.STRAT_FILE, kind)

    def test_parse_regions(self):
        regions = self._parse()
        self.assertEqual([r["id"] for r in regions], [101, 102])
        self.assertEqual(regions[0]["provinces"], [1, 2, 3])
        self.assertEqual(regions[1]["provinces"], [4, 5])

    def test_parse_unknown_kind_empty(self):
        from map_region_ops import parse_region_file
        self.assertEqual(parse_region_file("x = { id = 1 }", "nope"), [])

    def test_set_region_provinces_replaces(self):
        from map_region_ops import parse_region_file, set_region_provinces
        content = set_region_provinces(self.STRAT_FILE,
                                       "strategic_region", 101, [7, 8, 9, 10])
        regions = parse_region_file(content, "strategic_region")
        self.assertEqual(regions[0]["provinces"], [7, 8, 9, 10])
        # 其余区域与注释不动
        self.assertEqual(regions[1]["provinces"], [4, 5])
        self.assertIn("STRATEGICREGION_101", content)

    def test_append_region_and_next_id(self):
        from map_region_ops import (append_region, next_region_id,
                                    parse_region_file)
        regions = self._parse()
        self.assertEqual(next_region_id(regions), 103)
        content = append_region(self.STRAT_FILE, "strategic_region",
                                103, [20, 21])
        regions = parse_region_file(content, "strategic_region")
        self.assertEqual([r["id"] for r in regions], [101, 102, 103])
        self.assertEqual(regions[2]["provinces"], [20, 21])

    def test_append_when_missing_and_remove(self):
        from map_region_ops import (parse_region_file, remove_region,
                                    set_region_provinces)
        # 目标区域不存在 → set 退化为追加
        content = set_region_provinces(self.STRAT_FILE,
                                       "strategic_region", 999, [1, 2])
        self.assertEqual([r["id"] for r in
                          parse_region_file(content, "strategic_region")],
                         [101, 102, 999])
        # 删除
        content2 = remove_region(content, "strategic_region", 999)
        self.assertEqual([r["id"] for r in
                          parse_region_file(content2, "strategic_region")],
                         [101, 102])
        self.assertIsNone(remove_region(content2, "strategic_region", 999))

    def test_supply_area_and_state_kinds(self):
        from map_region_ops import parse_region_file
        sup = "supply_area = {\n\tid = 7\n\tprovinces = { 11 12 }\n}\n"
        self.assertEqual(parse_region_file(sup, "supply_area")[0]["provinces"],
                         [11, 12])
        st = "state = {\n\tid = 3\n\tprovinces = { 31 32 33 }\n}\n"
        self.assertEqual(parse_region_file(st, "state")[0]["id"], 3)


class StateEditOpsTest(unittest.TestCase):
    """state_edit_ops 归属写回契约。"""

    STATE_FILE = (
        "state = {\n"
        "\tid = 5\n"
        "\tname = \"STATE_5\"\n"
        "\thistory = {\n"
        "\t\towner = GER\n"
        "\t}\n"
        "\tprovinces = { 10 11 12 }\n"
        "}\n"
        "# comment kept\n"
    )

    def test_replace_owner(self):
        from state_edit_ops import set_state_owner_in_content
        content = set_state_owner_in_content(self.STATE_FILE, 5, "sov")
        self.assertIn("owner = SOV", content)
        self.assertNotIn("owner = GER", content)
        self.assertIn("# comment kept", content)
        self.assertIn("provinces = { 10 11 12 }", content)

    def test_insert_owner_when_missing(self):
        from state_edit_ops import set_state_owner_in_content
        # 无 history 块文件：插入 history + owner
        no_history = (
            "state = {\n\tid = 6\n\tprovinces = { 1 }\n}\n")
        content = set_state_owner_in_content(no_history, 6, "USA")
        self.assertIn("owner = USA", content)
        self.assertIn("history = {", content)
        # 有 history 无 owner：块内插入
        no_owner = (
            "state = {\n\tid = 7\n\thistory = {\n\t}\n\tprovinces = { 2 }\n}\n")
        content2 = set_state_owner_in_content(no_owner, 7, "JAP")
        self.assertIn("owner = JAP", content2)
        self.assertIn("provinces = { 2 }", content2)

    def test_state_not_found(self):
        from state_edit_ops import set_state_owner_in_content
        self.assertIsNone(set_state_owner_in_content(self.STATE_FILE, 999,
                                                     "GER"))

    def test_set_state_owner_writes_file(self):
        """文件级写回：原子写 + 内容正确 + 撤销快照。"""
        from state_edit_ops import set_state_owner
        from write_utils import atomic_write_text
        from undo_mgr import get_undo_manager
        mod = _mkdtemp("dsh_statemod_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "history", "states"))
        fp = os.path.join(mod, "history", "states", "5-name.txt")
        atomic_write_text(fp, self.STATE_FILE, undo=False)
        get_undo_manager().clear()
        ok, message, rel = set_state_owner(mod, 5, "FRA")
        self.assertTrue(ok, (message, rel))
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("owner = FRA", content)
        self.assertNotIn("owner = GER", content)
        # 撤销快照已登记
        self.assertTrue(get_undo_manager().can_undo())
        get_undo_manager().clear()

    def test_set_state_owner_not_in_mod(self):
        from state_edit_ops import set_state_owner
        mod = _mkdtemp("dsh_statemod2_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        ok, message, rel = set_state_owner(mod, 5, "FRA")
        self.assertFalse(ok)
        self.assertEqual(message, "not_found")


class StateExtLoaderTest(unittest.TestCase):
    """state_loader 扩展字段（州类别/人力/建筑/胜利点/建筑位）契约。"""

    STATE_FILE = (
        "state = {\n"
        "\tid = 5\n"
        "\tname = \"STATE_5\"\n"
        "\tmanpower = 123456\n"
        "\tstate_category = town\n"
        "\thistory = {\n"
        "\t\towner = GER\n"
        "\t\tvictory_points = { 10 2 11 1 }\n"
        "\t\tbuildings = {\n"
        "\t\t\tinfrastructure = 2\n"
        "\t\t\tair_base = 1\n"
        "\t\t\t10 = { naval_base = 3 anti_air_building = 1 }\n"
        "\t\t}\n"
        "\t}\n"
        "\tprovinces = { 10 11 12 }\n"
        "}\n"
    )

    def _state_data(self, mod, game=None, extra=""):
        from state_loader import StateData
        os.makedirs(os.path.join(mod, "history", "states"), exist_ok=True)
        with open(os.path.join(mod, "history", "states", "5-x.txt"),
                  "w", encoding="utf-8") as f:
            f.write(self.STATE_FILE + extra)
        os.makedirs(os.path.join(mod, "common", "state_category"),
                    exist_ok=True)
        with open(os.path.join(mod, "common", "state_category", "c.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state_categories={\n"
                    "\ttown = {\n\t\tlocal_building_slots = 4\n\t}\n"
                    "\trural = {\n\t\tlocal_building_slots = 2\n\t}\n"
                    "}\n")
        return StateData(mod, game or "")

    def test_parse_extended_fields(self):
        mod = _mkdtemp("dsh_stateext_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        sd = self._state_data(mod)
        info = sd.states[5]
        self.assertEqual(info["state_category"], "town")
        self.assertEqual(info["manpower"], 123456)
        self.assertEqual(info["buildings"],
                         {"infrastructure": 2, "air_base": 1})
        self.assertEqual(info["buildings_pid"],
                         {10: {"naval_base": 3, "anti_air_building": 1}})
        self.assertEqual(info["victory_points"], [(10, 2), (11, 1)])
        # 兼容字段保持（OOB 用）
        self.assertEqual(info["air_level"], 1)
        self.assertEqual(info["naval"], {10: 3})
        # 源文件记录（mod 优先）
        self.assertIn("5-x.txt", info["src"])

    def test_building_slots(self):
        mod = _mkdtemp("dsh_stateext2_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        sd = self._state_data(mod)
        self.assertEqual(sd.slots_of(5), 4)
        self.assertEqual(sd.category_slots("rural"), 2)
        self.assertEqual(sd.category_slots("unknown"), 0)
        self.assertEqual(sd.slots_of(999), 0)

    def test_buildings_of_aggregates(self):
        mod = _mkdtemp("dsh_stateext3_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        sd = self._state_data(mod)
        agg = sd.buildings_of(5)
        self.assertEqual(agg["infrastructure"], 2)
        self.assertEqual(agg["naval_base"], 3)
        self.assertEqual(agg["anti_air_building"], 1)


class BuildingLibTest(unittest.TestCase):
    """building_lib 建筑类型/国家颜色解析契约。"""

    def _game(self, extra_files=None):
        game = _mkdtemp("dsh_buildlib_")
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "common", "buildings"), exist_ok=True)
        with open(os.path.join(game, "common", "buildings", "00_b.txt"),
                  "w", encoding="utf-8") as f:
            f.write("buildings = {\n"
                    "\tinfrastructure = {\n\t\tvalue = 1\n"
                    "\t\tstate_modifiers = {\n"
                    "\t\t\tmodifiers = {\n"
                    "\t\t\t\tsupply_consumption_factor = -0.05\n"
                    "\t\t\t}\n"
                    "\t\t}\n"
                    "\t\tcountry_modifiers = {\n"
                    "\t\t\tmax_fuel_building = 1.5\n"
                    "\t\t}\n"
                    "\t}\n"
                    "\tnaval_base = {\n\t\tprovince_max = 10\n\t}\n"
                    "\tlandmark_test = {\n"
                    "\t\tprovince_max = 1\n\t\tis_buildable = no\n\t}\n"
                    "}\n")
        os.makedirs(os.path.join(game, "common", "countries"), exist_ok=True)
        with open(os.path.join(game, "common", "countries", "GBR.txt"),
                  "w", encoding="utf-8") as f:
            f.write("color = { 51 204 51 }\n")
        with open(os.path.join(game, "common", "countries", "Germany.txt"),
                  "w", encoding="utf-8") as f:
            f.write("country_tag = GER\n"
                    "color = { 0.2 0.4 0.6 }\n")
        return game

    def test_building_types(self):
        from building_lib import load_building_types
        game = self._game()
        types = load_building_types("", game)
        by_key = {t["key"]: t for t in types}
        self.assertFalse(by_key["infrastructure"]["provincial"])
        self.assertTrue(by_key["naval_base"]["provincial"])
        # is_buildable = no → 不可建造
        self.assertTrue(by_key["infrastructure"]["buildable"])
        self.assertTrue(by_key["naval_base"]["buildable"])
        self.assertFalse(by_key["landmark_test"]["buildable"])
        # icon_frame 解析（缺失时 None）
        self.assertIsNone(by_key["infrastructure"]["icon_frame"])
        # 来源标记（图标按来源选择图集）
        self.assertEqual(by_key["infrastructure"]["src"], "game")
        # 游戏内效果（state/country_modifiers，含嵌套 modifiers 块）
        mods = by_key["infrastructure"]["modifiers"]
        self.assertIn({"key": "supply_consumption_factor",
                       "value": -0.05, "scope": "state"}, mods)
        self.assertIn({"key": "max_fuel_building",
                       "value": 1.5, "scope": "country"}, mods)
        self.assertEqual(by_key["naval_base"]["modifiers"], [])

    def test_building_src_and_strip_frames(self):
        """来源标记 + GFX_buildings_strip noOfFrames 解析。"""
        from building_lib import load_building_types, strip_frame_count
        mod = _mkdtemp("dsh_bldsrc_")
        game = _mkdtemp("dsh_bldsrcg_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        for base, key, frame in ((mod, "mod_building", 3),
                                 (game, "game_building", 5)):
            os.makedirs(os.path.join(base, "common", "buildings"),
                        exist_ok=True)
            with open(os.path.join(base, "common", "buildings", "b.txt"),
                      "w", encoding="utf-8") as f:
                f.write("buildings = {\n\t%s = {\n\t\ticon_frame = %d\n"
                        "\t}\n}\n" % (key, frame))
        # mod 的 gfx 定义帧数不同
        os.makedirs(os.path.join(mod, "interface"), exist_ok=True)
        with open(os.path.join(mod, "interface", "x.gfx"),
                  "w", encoding="utf-8") as f:
            f.write('spriteType = {\n\tname = "GFX_buildings_strip"\n'
                    '\ttextureFile = "x.dds"\n\tnoOfFrames = 26\n}\n')
        types = load_building_types(mod, game)
        by_key = {t["key"]: t for t in types}
        self.assertEqual(by_key["mod_building"]["src"], "mod")
        self.assertEqual(by_key["game_building"]["src"], "game")
        self.assertEqual(strip_frame_count(mod), 26)
        self.assertEqual(strip_frame_count(game), 0)

    def test_country_colors(self):
        from building_lib import load_country_colors
        game = self._game()
        colors = load_country_colors("", game)
        # 文件名兜底（GBR.txt 无 country_tag）
        self.assertEqual(colors["GBR"], (51, 204, 51))
        # country_tag 匹配（Germany.txt → GER，浮点转 0-255）
        self.assertEqual(colors["GER"], (51, 102, 153))

    def test_country_color_float(self):
        from building_lib import load_country_colors
        game = _mkdtemp("dsh_buildlib2_")
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "common", "countries"), exist_ok=True)
        with open(os.path.join(game, "common", "countries", "USA.txt"),
                  "w", encoding="utf-8") as f:
            f.write("color = { 0.2 0.4 0.6 }\n")
        colors = load_country_colors("", game)
        self.assertEqual(colors["USA"], (51, 102, 153))


class StateBuildOpsTest(unittest.TestCase):
    """state_build_ops 建筑/州类别/国家颜色写回契约。"""

    STATE_FILE = (
        "state = {\n"
        "\tid = 5\n"
        "\tname = \"STATE_5\"\n"
        "\tstate_category = town\n"
        "\thistory = {\n"
        "\t\towner = GER\n"
        "\t\tbuildings = {\n"
        "\t\t\tinfrastructure = 2\n"
        "\t\t\t10 = { naval_base = 3 }\n"
        "\t\t}\n"
        "\t}\n"
        "\tprovinces = { 10 11 12 }\n"
        "}\n"
    )

    def test_set_building_top_level(self):
        from state_build_ops import set_state_building_in_content
        c = set_state_building_in_content(self.STATE_FILE, 5,
                                          "infrastructure", 5)
        self.assertIn("infrastructure = 5", c)
        self.assertNotIn("infrastructure = 2", c)
        c2 = set_state_building_in_content(self.STATE_FILE, 5,
                                           "industrial_complex", 2)
        self.assertIn("industrial_complex = 2", c2)
        # 删除不存在的建筑：无操作（None）
        c3 = set_state_building_in_content(self.STATE_FILE, 5,
                                           "industrial_complex", 0)
        self.assertIsNone(c3)
        # 删除存在的建筑
        c4 = set_state_building_in_content(self.STATE_FILE, 5,
                                           "infrastructure", 0)
        self.assertNotIn("infrastructure = ", c4)

    def test_set_building_anchored(self):
        from state_build_ops import set_state_building_in_content
        c = set_state_building_in_content(self.STATE_FILE, 5,
                                          "naval_base", 5, pid=10)
        self.assertIn("naval_base = 5", c)
        self.assertNotIn("naval_base = 3", c)
        c2 = set_state_building_in_content(self.STATE_FILE, 5,
                                           "radar_station", 1, pid=11)
        self.assertIn("11 = {", c2)
        self.assertIn("radar_station = 1", c2)
        # 删除后空块整体移除
        c3 = set_state_building_in_content(self.STATE_FILE, 5,
                                           "naval_base", 0, pid=10)
        self.assertNotIn("10 = {", c3)

    def test_set_category_and_country_color(self):
        from state_build_ops import (set_state_category_in_content,
                                     set_country_color_in_content)
        c = set_state_category_in_content(self.STATE_FILE, 5, "city")
        self.assertIn("state_category = city", c)
        self.assertNotIn("state_category = town", c)
        c2 = set_country_color_in_content("color = { 1 2 3 } #c\n",
                                          (255, 0, 128))
        self.assertIn("color = { 255 0 128 }", c2)
        self.assertIn("#c", c2)

    def _make_env(self):
        """mod + game 双目录：州文件只在 game。"""
        mod = _mkdtemp("dsh_buildmod_")
        game = _mkdtemp("dsh_buildgame_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "history", "states"), exist_ok=True)
        with open(os.path.join(game, "history", "states", "5-x.txt"),
                  "w", encoding="utf-8") as f:
            f.write(self.STATE_FILE)
        os.makedirs(os.path.join(game, "common", "countries"), exist_ok=True)
        with open(os.path.join(game, "common", "countries", "GER.txt"),
                  "w", encoding="utf-8") as f:
            f.write("color = { 51 204 51 }\n")
        return mod, game

    def test_write_building_copies_from_game(self):
        """原版州文件：自动复制到 mod 再写。"""
        from state_build_ops import set_state_building
        mod, game = self._make_env()
        ok, message, rel = set_state_building(
            mod, game, 5, "infrastructure", 4, pid=None, state_data=None)
        self.assertTrue(ok, message)
        self.assertEqual(message, "copied_written")
        fp = os.path.join(mod, "history", "states", "5-x.txt")
        self.assertTrue(os.path.isfile(fp), "原版文件应复制到 mod")
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("infrastructure = 4", content)
        self.assertIn("owner = GER", content)

    def test_write_building_in_mod_direct(self):
        """mod 已有州文件：直接写。"""
        from state_build_ops import set_state_building
        mod, game = self._make_env()
        os.makedirs(os.path.join(mod, "history", "states"), exist_ok=True)
        with open(os.path.join(mod, "history", "states", "5-x.txt"),
                  "w", encoding="utf-8") as f:
            f.write(self.STATE_FILE)
        ok, message, rel = set_state_building(
            mod, game, 5, "air_base", 2)
        self.assertTrue(ok, message)
        self.assertEqual(message, "written")
        with open(os.path.join(mod, "history", "states", "5-x.txt"),
                  "r", encoding="utf-8") as f:
            self.assertIn("air_base = 2", f.read())

    def test_write_country_color_copies_from_game(self):
        """原版国家文件：自动复制到 mod 再改 color。"""
        from state_build_ops import set_country_color
        mod, game = self._make_env()
        ok, message, rel = set_country_color(mod, game, "GER", (1, 2, 3))
        self.assertTrue(ok, message)
        self.assertEqual(message, "copied_written")
        fp = os.path.join(mod, "common", "countries", "GER.txt")
        self.assertTrue(os.path.isfile(fp))
        with open(fp, "r", encoding="utf-8") as f:
            self.assertIn("color = { 1 2 3 }", f.read())

    def test_write_state_category(self):
        from state_build_ops import set_state_category
        mod, game = self._make_env()
        ok, message, rel = set_state_category(mod, game, 5, "city")
        self.assertTrue(ok, message)
        with open(os.path.join(mod, "history", "states", "5-x.txt"),
                  "r", encoding="utf-8") as f:
            self.assertIn("state_category = city", f.read())


class MapEditorDialogSmokeTest(unittest.TestCase):
    """地图编辑器三栏布局冒烟（offscreen）：建筑列表/右面板/信息刷新。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        """临时 mod+game：小地图 + 州文件 + 建筑/类别/国家颜色。"""
        from PyQt6.QtGui import QColor, QImage
        mod = _mkdtemp("dsh_medit_")
        game = _mkdtemp("dsh_meditg_")
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
                        (pid * 10) % 256, (pid * 20) % 256,
                        (pid * 30) % 256))
            img.save(os.path.join(base, "map", "provinces.bmp"), "BMP")
            with open(os.path.join(base, "map", "definition.csv"),
                      "w", encoding="utf-8") as f:
                f.write("id;R;G;B;type;coastal;terrain;region\n")
                f.write("1;10;20;30;land;false;plains;1\n")
                f.write("2;20;40;60;land;false;plains;1\n")
        # 州文件：只在 game（验证原版复制路径）
        with open(os.path.join(game, "history", "states", "1-x.txt"),
                  "w", encoding="utf-8") as f:
            f.write(
                "state = {\n"
                "\tid = 1\n"
                "\tname = \"STATE_1\"\n"
                "\tstate_category = town\n"
                "\thistory = {\n"
                "\t\towner = GER\n"
                "\t\tbuildings = {\n"
                "\t\t\tinfrastructure = 2\n"
                "\t\t}\n"
                "\t}\n"
                "\tprovinces = { 1 2 }\n"
                "}\n")
        os.makedirs(os.path.join(game, "common", "state_category"),
                    exist_ok=True)
        with open(os.path.join(game, "common", "state_category", "c.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state_categories={\n"
                    "\ttown = {\n\t\tlocal_building_slots = 4\n\t}\n}\n")
        os.makedirs(os.path.join(game, "common", "buildings"), exist_ok=True)
        with open(os.path.join(game, "common", "buildings", "b.txt"),
                  "w", encoding="utf-8") as f:
            f.write("buildings = {\n"
                    "\tinfrastructure = {\n\t\tvalue = 1\n\t}\n"
                    "\tnaval_base = {\n\t\tprovince_max = 10\n\t}\n"
                    "}\n")
        os.makedirs(os.path.join(game, "common", "countries"), exist_ok=True)
        with open(os.path.join(game, "common", "countries", "GER.txt"),
                  "w", encoding="utf-8") as f:
            f.write("color = { 51 204 51 }\n")
        return mod, game

    def test_dialog_builds_and_info(self):
        """三栏布局：建筑列表非空、点选地块刷新右面板（含州类别/建筑位）。"""
        from map_editor_dialog import MapEditorDialog
        from oob_map_editor import _STATE_CACHE
        mod, game = self._make_env()
        _STATE_CACHE.clear()
        dlg = MapEditorDialog(mod_path=mod, game_path=game)
        dlg.show()
        self.app.processEvents()
        # 左：建筑类型按钮（可建造=纯图标，不可建造=文本，一个 QButtonGroup）
        buttons = dlg.building_group.buttons()
        self.assertGreater(len(buttons), 0)
        # 测试环境无 is_buildable=no → 全部可建造（纯图标）
        icon_only = [b for b in buttons if b.text() == ""]
        self.assertEqual(len(icon_only), len(buttons),
                         "可建造建筑应为纯图标按钮（无文本）")
        tips = [b.toolTip() for b in buttons]
        self.assertTrue(any("infrastructure" in t for t in tips))
        # 中：画布；右：信息面板
        self.assertIsNotNone(dlg.canvas)
        # 点选地块 → 右侧信息含州类别/建筑位/建筑/归属
        dlg._on_province_clicked(1, 0, 0)
        text = dlg.info_label.text()
        self.assertIn("地块 1", text)
        self.assertIn("州 1", text)
        self.assertIn("类别 town", text)
        self.assertIn("建筑位 4", text)
        self.assertIn("infrastructure 2", text)
        self.assertIn("GER", text)
        self.assertTrue(dlg.place_btn.isEnabled())
        self.assertTrue(dlg.owner_btn.isEnabled())
        self.assertTrue(dlg.color_btn.isEnabled())
        # 点选 = 单选（替换选中集，黄色选中层）
        self.assertEqual(dlg.canvas.selection(), [1])
        dlg.close()
        _STATE_CACHE.clear()

    def test_click_selects_single_province(self):
        """点选地块进入选中（替换）；再点其他省替换。"""
        from map_editor_dialog import MapEditorDialog
        from oob_map_editor import _STATE_CACHE
        mod, game = self._make_env()
        _STATE_CACHE.clear()
        dlg = MapEditorDialog(mod_path=mod, game_path=game)
        dlg.show()
        self.app.processEvents()
        dlg._on_province_clicked(1, 0, 0)
        self.assertEqual(dlg.canvas.selection(), [1])
        self.assertIn("地块 1", dlg.info_label.text())
        dlg._on_province_clicked(2, 0, 0)
        self.assertEqual(dlg.canvas.selection(), [2],
                         "点选另一省应替换选中集")
        dlg.close()
        _STATE_CACHE.clear()

    def test_hover_no_info_update(self):
        """悬停不再刷新右侧信息（只做目标省高亮）。"""
        from map_editor_dialog import MapEditorDialog
        from oob_map_editor import _STATE_CACHE
        mod, game = self._make_env()
        _STATE_CACHE.clear()
        dlg = MapEditorDialog(mod_path=mod, game_path=game)
        dlg.show()
        self.app.processEvents()
        self.assertTrue(dlg.canvas.hover_highlight_enabled(),
                        "地图编辑器应开启目标省高亮")
        dlg.info_label.setText("初始文本")
        dlg.canvas._set_hover(1)
        self.assertTrue(dlg.canvas.hover_item.isVisible(),
                        "悬停目标省应高亮")
        self.assertEqual(dlg.info_label.text(), "初始文本",
                         "悬停不应更新右侧信息")
        dlg.canvas.clear_hover()
        dlg.close()
        _STATE_CACHE.clear()

    def test_building_panel_layout(self):
        """建筑选区：图标放大、面板加宽、隐藏水平滚动条。"""
        from PyQt6.QtCore import Qt
        from map_editor_dialog import MapEditorDialog
        from oob_map_editor import _STATE_CACHE
        mod, game = self._make_env()
        _STATE_CACHE.clear()
        dlg = MapEditorDialog(mod_path=mod, game_path=game)
        dlg.show()
        self.app.processEvents()
        # 图标按钮放大（>= 56px）
        icon_only = [b for b in dlg.building_group.buttons()
                     if b.text() == ""]
        self.assertTrue(icon_only)
        self.assertGreaterEqual(icon_only[0].width(), 56)
        self.assertGreaterEqual(icon_only[0].height(), 56)
        # 图标在按钮内占比高（iconSize 接近按钮尺寸）
        self.assertGreaterEqual(icon_only[0].iconSize().width(), 52)
        self.assertGreaterEqual(icon_only[0].iconSize().height(), 52)
        # 左侧滚动区加宽 + 底部无水平滚动条
        self.assertGreaterEqual(dlg.building_scroll.minimumWidth(), 320)
        self.assertEqual(
            dlg.building_scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        dlg.close()
        _STATE_CACHE.clear()

    def test_selection_shows_state_outline(self):
        """选中地块后出现州轮廓高亮；清空选区后消失。"""
        from map_editor_dialog import MapEditorDialog
        from oob_map_editor import _STATE_CACHE
        mod, game = self._make_env()
        _STATE_CACHE.clear()
        dlg = MapEditorDialog(mod_path=mod, game_path=game)
        dlg.show()
        self.app.processEvents()
        dlg._on_province_clicked(1, 0, 0)
        self.assertEqual(len(dlg.canvas._state_outline_items), 1,
                         "选中州内地块后应显示 1 个州轮廓")
        dlg.canvas.clear_selection()
        self.assertEqual(len(dlg.canvas._state_outline_items), 0,
                         "清空选区后应清除州轮廓")
        dlg.close()
        _STATE_CACHE.clear()


class RegionScanTest(unittest.TestCase):
    """scan_region_files mod 优先契约。"""

    def test_scan_mod_preferred_over_game(self):
        from map_region_ops import scan_region_files
        mod = _mkdtemp("dsh_scanmod_")
        game = _mkdtemp("dsh_scangame_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        for base, rid in ((mod, 1), (game, 2)):
            d = os.path.join(base, "map", "strategicregions")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "regions.txt"), "w",
                      encoding="utf-8") as f:
                f.write("strategic_region = {\n\tid = %d\n"
                        "\tprovinces = { 1 2 }\n}\n" % rid)
        files = scan_region_files(mod, game)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["source"], "mod")
        self.assertEqual(files[0]["regions"][0]["id"], 1)


class MapCanvasPureTest(unittest.TestCase):
    """map_canvas / map_loader 纯函数契约（无 GUI）。"""

    def test_pids_in_rect(self):
        import numpy as np
        from map_canvas import pids_in_rect
        idm = np.zeros((10, 10), dtype=np.uint32)
        idm[2:5, 2:5] = 7
        idm[6:8, 6:8] = 9
        self.assertEqual(sorted(pids_in_rect(idm, 1, 1, 4, 4)), [7])
        self.assertEqual(sorted(pids_in_rect(idm, 0, 0, 9, 9)), [7, 9])
        self.assertEqual(pids_in_rect(idm, 0, 0, 1, 1), [])
        # 坐标顺序无关、越界安全
        self.assertEqual(sorted(pids_in_rect(idm, 4, 4, 1, 1)), [7])
        self.assertEqual(pids_in_rect(idm, -5, -5, 100, 100), [7, 9])

    def test_hillshade_array(self):
        import numpy as np
        from map_loader import hillshade_array
        h = np.zeros((8, 8), dtype=np.float32)
        h[2:6, 2:6] = 100.0   # 平台
        shade = hillshade_array(h)
        self.assertEqual(shade.shape, (8, 8))
        self.assertEqual(shade.dtype, np.uint8)
        # 平坦区域：法线垂直向上，光照近垂直 → 亮（>200）
        self.assertGreater(shade[4, 4], 200)
        self.assertLess(shade[4, 4], 255)
        # 全平退化
        shade2 = hillshade_array(np.zeros((4, 4), dtype=np.float32))
        self.assertTrue((shade2 >= 0).all() and (shade2 <= 255).all())


class MapVectorTest(unittest.TestCase):
    """map_vector 边界线段提取契约。"""

    def test_build_edge_segments_square(self):
        import numpy as np
        from map_vector import build_edge_segments
        idm = np.zeros((5, 5), dtype=np.uint32)
        idm[1:4, 1:4] = 7          # 3x3 方块
        segs = build_edge_segments(idm)
        # 方块四条边：每边 3 像素段合并为 1 条线段 → 共 4 条
        self.assertEqual(segs.shape[0], 4)
        # 竖直线段 x0==x1；水平线段 y0==y1
        v = segs[segs[:, 0] == segs[:, 2]]
        hsegs = segs[segs[:, 1] == segs[:, 3]]
        self.assertEqual(v.shape[0], 2)     # 左右两条竖边
        self.assertEqual(hsegs.shape[0], 2)  # 上下两条横边
        # 左竖边：x=1，y 从 1 到 4
        left = v[v[:, 0] == 1]
        self.assertEqual(len(left), 1)
        self.assertEqual((left[0, 1], left[0, 3]), (1, 4))

    def test_build_edge_segments_sea_filter(self):
        import numpy as np
        from map_vector import build_edge_segments
        # 两块海铺满矩阵：唯一边界是海-海共享边 → 全部剔除
        idm2 = np.zeros((4, 4), dtype=np.uint32)
        idm2[:, :2] = 9
        idm2[:, 2:] = 11
        f2 = build_edge_segments(idm2, sea_pids=[9, 11])
        self.assertEqual(f2.shape[0], 0)
        # 陆-海相邻：海岸线保留（3 段合并 1 条）
        idm3 = np.zeros((4, 4), dtype=np.uint32)
        idm3[:, :2] = 7
        idm3[:, 2:] = 9
        f3 = build_edge_segments(idm3, sea_pids=[9])
        self.assertEqual(f3.shape[0], 1)


class MapSettingsTest(unittest.TestCase):
    """map_canvas 可调参数（settings.json map_* 键）契约。"""

    def test_defaults_when_missing(self):
        from map_canvas import read_map_settings
        d = _mkdtemp("dsh_mapcfg_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        cfg = read_map_settings(os.path.join(d, "none.json"))
        self.assertEqual(cfg["zoom_threshold"], 2.5)
        self.assertEqual(cfg["zoom_settle_ms"], 300)
        self.assertEqual(cfg["initial_zoom"], 1.3)

    def test_initial_zoom_custom_and_clamp(self):
        from map_canvas import read_map_settings
        d = _mkdtemp("dsh_mapcfg_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        fp = os.path.join(d, "settings.json")
        with open(fp, "w", encoding="utf-8") as f:
            f.write('{"map_initial_zoom": 1.6}')
        self.assertEqual(read_map_settings(fp)["initial_zoom"], 1.6)
        with open(fp, "w", encoding="utf-8") as f:
            f.write('{"map_initial_zoom": 0.5}')
        # 下限保护：不小于 1.0（不缩小到比全景还小）
        self.assertEqual(read_map_settings(fp)["initial_zoom"], 1.0)
        with open(fp, "w", encoding="utf-8") as f:
            f.write('{"map_initial_zoom": 99}')
        self.assertEqual(read_map_settings(fp)["initial_zoom"], 4.0)

    def test_custom_values(self):
        from map_canvas import read_map_settings
        d = _mkdtemp("dsh_mapcfg_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        fp = os.path.join(d, "settings.json")
        with open(fp, "w", encoding="utf-8") as f:
            f.write('{"map_zoom_threshold": 4.0, "map_zoom_settle_ms": 350}')
        cfg = read_map_settings(fp)
        self.assertEqual(cfg["zoom_threshold"], 4.0)
        self.assertEqual(cfg["zoom_settle_ms"], 350)

    def test_bad_values_fall_back(self):
        from map_canvas import read_map_settings
        d = _mkdtemp("dsh_mapcfg_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        fp = os.path.join(d, "settings.json")
        with open(fp, "w", encoding="utf-8") as f:
            f.write('{"map_zoom_threshold": "abc", "map_zoom_settle_ms": -1}')
        cfg = read_map_settings(fp)
        self.assertEqual(cfg["zoom_threshold"], 2.5)
        # settle 下限保护（防 0/负数让防抖失效）
        self.assertGreaterEqual(cfg["zoom_settle_ms"], 50)

    def test_broken_json_falls_back(self):
        from map_canvas import read_map_settings
        d = _mkdtemp("dsh_mapcfg_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        fp = os.path.join(d, "settings.json")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("{broken")
        cfg = read_map_settings(fp)
        self.assertEqual(cfg["zoom_threshold"], 2.5)
        self.assertEqual(cfg["zoom_settle_ms"], 300)


class MapFillTest(unittest.TestCase):
    """map_fill 闭合轮廓提取契约（Marching Squares + DP）。"""

    @staticmethod
    def _signed_area(pts):
        import numpy as np
        x, y = pts[:, 0], pts[:, 1]
        return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)

    @staticmethod
    def _fill(idm, tol=1.0):
        from map_fill import build_province_polygons, FillData
        p = build_province_polygons(idm, tol=tol)
        return FillData(p["verts"], p["loop_off"], p["loop_pid"],
                        p["loop_bbox"])

    def test_square_minimal_vertices(self):
        import numpy as np
        idm = np.pad(np.full((4, 4), 7, np.uint32), 2)
        f = self._fill(idm)
        self.assertEqual(f.n_loops, 1)
        self.assertEqual(int(f.loop_pid[0]), 7)
        pts = f.loop_vertices(0)
        # 方块 → 4 个角点；面积 16；包围盒精确
        self.assertEqual(len(pts), 4)
        self.assertEqual(abs(self._signed_area(pts)), 16.0)
        np.testing.assert_allclose(f.loop_bbox[0], [2, 2, 6, 6])

    def test_two_provinces_share_edge(self):
        import numpy as np
        idm = np.zeros((5, 10), dtype=np.uint32)
        idm[:, :5] = 1
        idm[:, 5:] = 2
        f = self._fill(idm)
        self.assertEqual(sorted(int(p) for p in f.loop_pid), [1, 2])
        total = {}
        for li in range(f.n_loops):
            pid = int(f.loop_pid[li])
            total[pid] = total.get(pid, 0.0) + self._signed_area(
                f.loop_vertices(li))
        self.assertEqual(abs(total[1]), 25.0)
        self.assertEqual(abs(total[2]), 25.0)

    def test_ring_with_hole(self):
        import numpy as np
        idm = np.zeros((14, 14), dtype=np.uint32)
        idm[1:13, 1:13] = 7
        idm[3:11, 3:11] = 0
        idm[5:9, 5:9] = 9
        f = self._fill(idm)
        # pid7 两环（外 144 + 内 64，方向相反），pid9 一环（16）
        self.assertEqual(f.n_loops, 3)
        self.assertEqual(int(f.loop_pid[0]), 7)
        self.assertEqual(int(f.loop_pid[2]), 9)
        total7 = sum(self._signed_area(f.loop_vertices(li))
                     for li in range(f.n_loops)
                     if int(f.loop_pid[li]) == 7)
        self.assertEqual(abs(total7), 80.0)
        self.assertEqual(len(f.loop_vertices(1)), 4)

    def test_saddle_diagonal_neighbors(self):
        import numpy as np
        idm = np.zeros((2, 2), dtype=np.uint32)
        idm[0, 0] = 1
        idm[0, 1] = 2
        idm[1, 0] = 2
        idm[1, 1] = 1
        f = self._fill(idm)
        # 鞍点拆成 4 个独立单像素环（Marching Squares 断开语义）
        self.assertEqual(f.n_loops, 4)
        self.assertEqual(sorted(int(p) for p in f.loop_pid), [1, 1, 2, 2])
        for li in range(f.n_loops):
            self.assertEqual(abs(self._signed_area(f.loop_vertices(li))), 1.0)

    def test_pid0_skipped_map_border_closed(self):
        import numpy as np
        # 未映射区域（0）在内部：其邻省轮廓仍闭合，pid 0 无环
        idm = np.zeros((10, 10), dtype=np.uint32)
        idm[2:8, 2:8] = 5
        idm[4:6, 4:6] = 0
        f = self._fill(idm)
        self.assertTrue(all(int(p) != 0 for p in f.loop_pid))
        total = sum(self._signed_area(f.loop_vertices(li))
                    for li in range(f.n_loops))
        self.assertEqual(abs(total), 32.0)  # 6x6 - 2x2

    def test_dp_simplifies_and_preserves_area(self):
        import numpy as np
        idm = np.zeros((40, 60), dtype=np.uint32)
        idm[10:30, 10:50] = 3
        idm[12:28, 50:52] = 3   # 锯齿右边界
        raw = self._fill(idm, tol=0.0)
        simp = self._fill(idm, tol=1.0)
        self.assertLessEqual(len(simp.verts), len(raw.verts))
        self.assertGreaterEqual(len(raw.verts), 8)
        total_r = sum(self._signed_area(raw.loop_vertices(li))
                      for li in range(raw.n_loops))
        total_s = sum(self._signed_area(simp.loop_vertices(li))
                      for li in range(simp.n_loops))
        self.assertAlmostEqual(abs(total_r), abs(total_s), delta=2.0)

    def test_staircase_kept_at_low_tol(self):
        import numpy as np
        idm = np.zeros((12, 12), dtype=np.uint32)
        for i in range(8):
            idm[2 + i, 2:2 + 8 - i] = 3
        f = self._fill(idm, tol=1.0)
        pts = f.loop_vertices(0)
        # 台阶是真实角点：tol=1 不应过度简化（>10 点），面积 36
        self.assertGreater(len(pts), 10)
        self.assertEqual(abs(self._signed_area(pts)), 36.0)

    def test_cache_roundtrip(self):
        import numpy as np
        from map_fill import FillData
        idm = np.zeros((6, 6), dtype=np.uint32)
        idm[1:5, 1:5] = 4
        f = self._fill(idm)
        d = _mkdtemp("dsh_fillcache_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        fp = os.path.join(d, "t.npz")
        np.savez(fp, verts=f.verts, loop_off=f.loop_off,
                 loop_pid=f.loop_pid, loop_bbox=f.loop_bbox)
        with np.load(fp) as z:
            f2 = FillData(z["verts"], z["loop_off"], z["loop_pid"],
                          z["loop_bbox"])
        np.testing.assert_array_equal(f.verts, f2.verts)
        np.testing.assert_array_equal(f.loop_off, f2.loop_off)
        np.testing.assert_array_equal(f.loop_pid, f2.loop_pid)

    def test_get_province_polygons_from_mapdata(self):
        """MapData（临时 mod 目录）→ get_province_polygons 全链路。"""
        import numpy as np
        from PyQt6.QtGui import QColor, QImage
        from map_loader import MapData
        from map_fill import get_province_polygons
        mod = _mkdtemp("dsh_fillmd_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "map"), exist_ok=True)
        w, h = 8, 8
        img = QImage(w, h, QImage.Format.Format_RGB888)
        for y in range(h):
            for x in range(w):
                pid = 1 if x < 4 else 2
                img.setPixelColor(x, y, QColor(
                    (pid * 10) % 256, (pid * 20) % 256, (pid * 30) % 256))
        img.save(os.path.join(mod, "map", "provinces.bmp"), "BMP")
        with open(os.path.join(mod, "map", "definition.csv"), "w",
                  encoding="utf-8") as f:
            f.write("id;R;G;B;type;coastal;terrain;region\n")
            f.write("1;10;20;30;land;false;plains;1\n")
            f.write("2;20;40;60;land;false;plains;1\n")
        md = MapData(mod)
        fill = get_province_polygons(md)
        self.assertIsNotNone(fill)
        self.assertEqual(fill.n_loops, 2)
        self.assertEqual(sorted(int(p) for p in fill.loop_pid), [1, 2])
        # 矩形查询
        self.assertEqual(fill.pids_in_rect(2, 2, 3, 3), [1])
        self.assertEqual(fill.pids_in_rect(5, 2, 6, 3), [2])
        # 缓存目录已建立
        self.assertTrue(os.path.isdir(
            os.path.join(PROJECT_ROOT, ".runtime", "map_fill")))


class MapCanvasSmokeTest(unittest.TestCase):
    """MapCanvas + 矢量多边形填充渲染冒烟（offscreen）。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_map(self):
        """临时 mod 目录：8x8 两省地图（pid1 左 4 列，pid2 右 4 列）。"""
        from PyQt6.QtGui import QColor, QImage
        from map_loader import MapData
        mod = _mkdtemp("dsh_canvas_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "map"), exist_ok=True)
        img = QImage(8, 8, QImage.Format.Format_RGB888)
        for y in range(8):
            for x in range(8):
                pid = 1 if x < 4 else 2
                img.setPixelColor(x, y, QColor(
                    (pid * 10) % 256, (pid * 20) % 256, (pid * 30) % 256))
        img.save(os.path.join(mod, "map", "provinces.bmp"), "BMP")
        with open(os.path.join(mod, "map", "definition.csv"), "w",
                  encoding="utf-8") as f:
            f.write("id;R;G;B;type;coastal;terrain;region\n")
            f.write("1;10;20;30;land;false;plains;1\n")
            f.write("2;20;40;60;land;false;plains;1\n")
        return MapData(mod)

    def _dominant_color(self, img, x, y, w, h):
        """取样区最常见颜色（抗锯齿边缘容错）。"""
        from collections import Counter
        cnt = Counter()
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                c = img.pixelColor(xx, yy)
                cnt[(c.red(), c.green(), c.blue())] += 1
        return cnt.most_common(1)[0][0]

    def test_vector_fill_renders_sharp_colors(self):
        from map_canvas import MapCanvas
        from map_fill import get_province_polygons
        md = self._make_map()
        c = MapCanvas(md)
        c.resize(400, 300)
        c.show()
        self.app.processEvents()          # offscreen 布局就绪
        fill = get_province_polygons(md)
        self.assertIsNotNone(fill)
        c.enable_vector_fill(fill, threshold=2.0)
        c.scale(60, 60)            # 地图超出视口，centerOn 不再被钳制
        c.centerOn(2.5, 2.5)     # pid1 区域中心
        self.app.processEvents()
        img = c.grab().toImage()
        self.assertFalse(img.isNull())
        w, h = img.width(), img.height()
        color = self._dominant_color(img, w // 2 - 20, h // 2 - 20, 40, 40)
        self.assertEqual(color, (10, 20, 30),
                         "放大后中心应为 pid1 的平坦省色（矢量填充）")

    def test_fill_falls_back_to_pixmap_below_threshold(self):
        from map_canvas import MapCanvas
        from map_fill import get_province_polygons
        md = self._make_map()
        c = MapCanvas(md)
        c.resize(400, 300)
        c.show()
        self.app.processEvents()
        fill = get_province_polygons(md)
        c.enable_vector_fill(fill, threshold=999.0)   # 永不达阈值
        c.scale(3, 3)
        c.centerOn(4, 4)
        self.app.processEvents()
        img = c.grab().toImage()
        self.assertFalse(img.isNull())
        w, h = img.width(), img.height()
        # 中心 8x8 取样：命中 pid1/pid2 任一省色即可（位图路径）
        color = self._dominant_color(img, w // 2 - 4, h // 2 - 4, 8, 8)
        self.assertIn(color, [(10, 20, 30), (20, 40, 60)])

    def test_fit_map_factor(self):
        """初始视野：fit_map(factor) 在全景基础上放大；无 factor 保持全景。"""
        from map_canvas import MapCanvas
        md = self._make_map()
        c = MapCanvas(md)
        c.resize(400, 300)
        c.show()
        self.app.processEvents()
        c.fit_map()
        z_full = c.transform().m11()
        c.fit_map(factor=1.5)
        z_zoom = c.transform().m11()
        self.assertAlmostEqual(z_zoom, z_full * 1.5, places=3,
                               msg="fit_map(factor) 应在全景基础上放大")
        c.fit_map()
        self.assertAlmostEqual(c.transform().m11(), z_full, places=3,
                               msg="fit_map() 不传 factor 应恢复全景")

    def test_no_fill_data_renders(self):
        from map_canvas import MapCanvas
        md = self._make_map()
        c = MapCanvas(md)
        c.resize(400, 300)
        c.show()
        c.scale(5, 5)
        img = c.grab().toImage()
        self.assertFalse(img.isNull())

    # ---------------------------------------------------------- 矢量填充缓存

    def _fill_canvas(self):
        """8x8 两省地图 + 矢量填充 + 60x 缩放（瓦片路径）。"""
        from map_canvas import MapCanvas
        from map_fill import get_province_polygons
        md = self._make_map()
        c = MapCanvas(md)
        c.resize(400, 300)
        c.show()
        self.app.processEvents()
        fill = get_province_polygons(md)
        self.assertIsNotNone(fill)
        c.enable_vector_fill(fill, threshold=2.0)
        c.scale(60, 60)
        c.centerOn(2.5, 2.5)
        self.app.processEvents()
        return c

    def test_vector_fill_tile_cache_hits(self):
        """瓦片缓存：同缩放重复绘制应命中（不重渲染）。"""
        c = self._fill_canvas()
        c.grab()
        item = c.base_item
        self.assertIsNotNone(item._tile, "首次绘制后应生成瓦片")
        hits0 = item._tile_hits
        c.grab()
        self.assertGreater(item._tile_hits, hits0,
                           "同缩放重复绘制应命中瓦片缓存")
        img = c.grab().toImage()
        w, h = img.width(), img.height()
        color = self._dominant_color(img, w // 2 - 20, h // 2 - 20, 40, 40)
        self.assertEqual(color, (10, 20, 30),
                         "瓦片路径下中心仍应为 pid1 省色")

    def test_vector_fill_blit_matches_rerender(self):
        """瓦片 blit 与重渲染采样一致（同视图强制重渲染对比）。"""
        c = self._fill_canvas()
        c.grab()
        img1 = c.grab().toImage()            # blit 路径
        item = c.base_item
        self.assertIsNotNone(item._tile)
        item._tile = None                    # 强制下次重渲染
        item._tile_hits = 0
        img2 = c.grab().toImage()            # 重渲染路径
        self.assertIsNotNone(item._tile, "重渲染后应重新生成瓦片")
        w, h = img1.width(), img1.height()
        diffs = 0
        for yy in range(0, h, 6):
            for xx in range(0, w, 6):
                c1 = img1.pixelColor(xx, yy)
                c2 = img2.pixelColor(xx, yy)
                if (c1.red(), c1.green(), c1.blue()) != \
                        (c2.red(), c2.green(), c2.blue()):
                    diffs += 1
        self.assertEqual(diffs, 0, "blit 与重渲染采样应完全一致")

    def test_vector_fill_tile_invalidated_on_zoom_change(self):
        """缩放变化后瓦片应重渲染（缩放档变化 → 缓存失效）。"""
        c = self._fill_canvas()
        c.grab()
        z0 = c.base_item._tile[0]
        c.scale(1.5, 1.5)
        self.app.processEvents()
        c.grab()
        self.assertIsNotNone(c.base_item._tile)
        self.assertNotAlmostEqual(
            c.base_item._tile[0], z0,
            msg="缩放变化后瓦片应重渲染")

    def test_vector_fill_caches_cleared_on_fill_change(self):
        """关闭填充后瓦片与省级 path 缓存应清空。"""
        c = self._fill_canvas()
        c.grab()
        item = c.base_item
        self.assertGreater(len(item._path_cache), 0, "绘制后应构建省级 path")
        c.enable_vector_fill(None)
        self.assertIsNone(item._tile)
        self.assertEqual(len(item._path_cache), 0)

    def test_vector_fill_path_cache_odd_even(self):
        """省级 path 缓存：even-odd 填充规则（孔洞/多连通语义保留）。"""
        from PyQt6.QtCore import Qt
        c = self._fill_canvas()
        c.grab()
        item = c.base_item
        path = item._path_cache.get(1)
        self.assertIsNotNone(path, "pid1 的 path 应已缓存")
        self.assertEqual(path.fillRule(), Qt.FillRule.OddEvenFill)

    def test_vector_fill_tile_bakes_borders(self):
        """边界线烘焙进瓦片：省界附近有深色描边，瓦片标记含边界。"""
        from map_canvas import MapCanvas
        from map_fill import get_province_polygons
        from map_vector import build_edge_segments
        md = self._make_map()
        c = MapCanvas(md)
        c.resize(400, 300)
        c.show()
        self.app.processEvents()
        fill = get_province_polygons(md)
        c.enable_vector_borders(build_edge_segments(md.id_map))
        c.enable_vector_fill(fill, threshold=2.0)
        c.scale(60, 60)
        c.centerOn(2.5, 2.5)
        self.app.processEvents()
        img = c.grab().toImage()
        item = c.base_item
        self.assertIsNotNone(item._tile)
        self.assertTrue(item._tile[6], "瓦片应烘焙边界线")
        # 省界 x=4 → 设备 x≈290：附近应有深色描边像素
        dark = 0
        for yy in range(140, 161):
            for xx in range(286, 295):
                col = img.pixelColor(xx, yy)
                if col.red() < 60 and col.green() < 60 and col.blue() < 70:
                    dark += 1
        self.assertGreater(dark, 0, "省界附近应有深色描边像素")

    def test_tile_follows_pan(self):
        """回归：小幅平移（瓦片缓存命中）时色块应跟随地图移动。

        曾因 _blit_tile 把瓦片画死在固定设备偏移，pan 在缓存区内时
        色块钉在原地（中心颜色不随视图变化）。
        """
        c = self._fill_canvas()          # 8x8 两省, zoom 60, centerOn(2.5,2.5)
        c.grab()
        tile_before = c.base_item._tile
        self.assertIsNotNone(tile_before)
        # 平移 2 场景 px（120 设备 px < margin 200）→ 命中缓存不重渲染
        c.centerOn(4.5, 2.5)
        self.app.processEvents()
        img = c.grab().toImage()
        self.assertIs(c.base_item._tile, tile_before,
                      "小幅平移不应重渲染瓦片（应纯 blit 跟随）")
        w, h = img.width(), img.height()
        color = self._dominant_color(img, w // 2 - 10, h // 2 - 10, 20, 20)
        self.assertEqual(color, (20, 40, 60),
                         "平移后中心应显示 pid2 色（瓦片位置应跟随地图）")

    def test_tile_follows_preview_zoom(self):
        """回归：预览模式缩放时瓦片位置应跟随变换（锚点处内容不变）。"""
        c = self._fill_canvas()
        c.grab()
        c.base_item.set_preview_mode(True)
        c.scale(1.5, 1.5)                # 以视口中心为锚放大
        self.app.processEvents()
        img = c.grab().toImage()
        w, h = img.width(), img.height()
        color = self._dominant_color(img, w // 2 - 10, h // 2 - 10, 20, 20)
        self.assertIn(color, [(10, 20, 30), (20, 40, 60)],
                      "预览缩放后中心内容应仍在原位（位置跟随变换）")

    def test_blend_border_math(self):
        """_blend_border 预乘 alpha 混合数学（小端 0xAARRGGBB 回归）。"""
        import numpy as np
        from map_canvas import _blend_border
        vals = np.array([0xFF0A141E, 0x00000000, 0xFFFFFFFF],
                        dtype=np.uint32)
        _blend_border(vals, 200, 55, 40 * 200 // 255,
                      40 * 200 // 255, 45 * 200 // 255)
        # 不透明省色 (10,20,30) 上 → (33,35,41)；透明上 → A=200 (31,31,35)
        # 白色上 → (86,86,90)
        self.assertEqual(int(vals[0]), 0xFF212329)
        self.assertEqual(int(vals[1]), 0xC81F1F23)
        self.assertEqual(int(vals[2]), 0xFF56565A)

    def test_mask_overlay_white_edge(self):
        """高亮覆盖层：内部半透明、边缘 1px 白色不透明（醒目描边）。"""
        import numpy as np
        from map_canvas import MapCanvas
        idm = np.zeros((7, 7), dtype=np.uint32)
        idm[2:5, 2:5] = 7
        pm, x0, y0 = MapCanvas._mask_overlay(idm, [7], (255, 200, 90), 180)
        self.assertIsNotNone(pm)
        self.assertEqual((x0, y0), (2, 2))
        img = pm.toImage()
        # 内部 → 半透明黄（alpha 180）
        c_in = img.pixelColor(1, 1)
        self.assertEqual(c_in.alpha(), 180)
        self.assertGreater(c_in.red(), 200)
        # 边缘（顶边中点）→ 白色不透明
        c_ed = img.pixelColor(1, 0)
        self.assertEqual(c_ed.alpha(), 255)
        self.assertEqual((c_ed.red(), c_ed.green(), c_ed.blue()),
                         (255, 255, 255))

    # ---------------------------------------------------------- 滚轮预览缩放

    def test_preview_mode_uses_existing_tile(self):
        """预览模式：缩放变化不重渲染瓦片，直接用旧瓦片缩放显示。"""
        c = self._fill_canvas()
        c.grab()
        z0 = c.base_item._tile[0]
        self.assertGreater(z0, 0)
        c.base_item.set_preview_mode(True)
        c.scale(1.5, 1.5)
        self.app.processEvents()
        img = c.grab().toImage()
        self.assertAlmostEqual(
            c.base_item._tile[0], z0, places=3,
            msg="预览模式缩放不应重渲染瓦片（仍用旧 zoom 瓦片）")
        w, h = img.width(), img.height()
        color = self._dominant_color(img, w // 2 - 10, h // 2 - 10, 20, 20)
        self.assertIn(color, [(10, 20, 30), (20, 40, 60)],
                      "预览模式画面仍应有省色内容")

    def test_preview_mode_off_rerenders(self):
        """退出预览后：缩放不匹配 → 自动重渲染高质量瓦片。"""
        c = self._fill_canvas()
        c.grab()
        z0 = c.base_item._tile[0]
        c.base_item.set_preview_mode(True)
        c.scale(1.5, 1.5)
        self.app.processEvents()
        c.grab()
        c.base_item.set_preview_mode(False)
        c.grab()
        self.assertNotAlmostEqual(
            c.base_item._tile[0], z0, places=3,
            msg="退出预览后应按新 zoom 重渲染瓦片")

    def test_wheel_event_enters_preview(self):
        """wheelEvent：进入预览模式且不挂起重绘（画面实时缩放）。"""
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QWheelEvent
        c = self._fill_canvas()
        c.grab()
        ev = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, 120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False)
        c.wheelEvent(ev)
        self.assertTrue(c._preview_active, "滚轮应进入预览模式")
        self.assertTrue(c.base_item._preview_mode)
        self.assertTrue(c.updatesEnabled(),
                        "预览模式不应挂起重绘（updatesEnabled() 是方法）")
        # 预览结束：flush 后瓦片按新缩放重渲染
        z0 = c.base_item._tile[0]
        c._flush_zoom()
        self.assertFalse(c._preview_active)
        c.grab()
        self.assertNotAlmostEqual(c.base_item._tile[0], z0, places=3,
                                  msg="flush 后应按新 zoom 重渲染")

    def test_state_outline_overlay_draws_yellow_edge(self):
        """州轮廓纯函数：只画黄色外扩描边，内部不填充。"""
        from map_canvas import MapCanvas
        md = self._make_map()
        pm, x0, y0 = MapCanvas._state_outline_overlay(
            md.id_map, [1], (255, 200, 90), 255, width=2)
        self.assertIsNotNone(pm)
        self.assertEqual((x0, y0), (0, 0))
        img = pm.toImage()
        found_yellow = False
        for yy in range(img.height()):
            for xx in range(img.width()):
                c = img.pixelColor(xx, yy)
                if (c.alpha() == 255 and c.red() > 200
                        and 150 < c.green() < 250):
                    found_yellow = True
                    break
            if found_yellow:
                break
        self.assertTrue(found_yellow, "州轮廓应包含黄色描边像素")
        # pid1 内部（不在外扩边）应透明，即只描边不填充
        c_in = img.pixelColor(1, 1)
        self.assertEqual(c_in.alpha(), 0, "州轮廓内部不应填充")

    def test_set_state_outlines_and_clear(self):
        """set_state_outlines 添加州轮廓 item；clear 全部移除。"""
        from map_canvas import MapCanvas
        md = self._make_map()
        c = MapCanvas(md)
        c.resize(400, 300)
        c.show()
        self.app.processEvents()
        c.set_state_outlines([[1]])
        self.assertEqual(len(c._state_outline_items), 1,
                         "应创建一个州轮廓 item")
        c.clear_state_outlines()
        self.assertEqual(len(c._state_outline_items), 0,
                         "清除后不应残留州轮廓 item")
        c.close()


class MapCanvasExtensionsTest(unittest.TestCase):
    """MapCanvas 通用扩展点（点击/右键/悬停信号 + 前景 painter 钩子）。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_map(self):
        from PyQt6.QtGui import QColor, QImage
        from map_loader import MapData
        mod = _mkdtemp("dsh_ext_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "map"), exist_ok=True)
        img = QImage(8, 8, QImage.Format.Format_RGB888)
        for y in range(8):
            for x in range(8):
                pid = 1 if x < 4 else 2
                img.setPixelColor(x, y, QColor(
                    (pid * 10) % 256, (pid * 20) % 256, (pid * 30) % 256))
        img.save(os.path.join(mod, "map", "provinces.bmp"), "BMP")
        with open(os.path.join(mod, "map", "definition.csv"), "w",
                  encoding="utf-8") as f:
            f.write("id;R;G;B;type;coastal;terrain;region\n")
            f.write("1;10;20;30;land;false;plains;1\n")
            f.write("2;20;40;60;land;false;plains;1\n")
        return MapData(mod)

    def _canvas(self):
        from map_canvas import MapCanvas
        c = MapCanvas(self._make_map())
        c.resize(400, 300)
        c.show()
        self.app.processEvents()
        return c

    def test_left_click_signal(self):
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        c = self._canvas()
        got = []
        c.left_clicked.connect(lambda x, y: got.append((x, y)))
        QTest.mouseClick(c.viewport(), Qt.MouseButton.LeftButton,
                         pos=QPoint(60, 70))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0], (60, 70))

    def test_right_click_signal(self):
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        c = self._canvas()
        got = []
        c.right_clicked.connect(
            lambda x, y, g: got.append((x, y, type(g).__name__)))
        QTest.mouseClick(c.viewport(), Qt.MouseButton.RightButton,
                         pos=QPoint(40, 50))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][:2], (40, 50))
        self.assertEqual(got[0][2], "QPoint")

    def test_hover_moved_signal(self):
        from PyQt6.QtCore import QPoint
        from PyQt6.QtTest import QTest
        c = self._canvas()
        got = []
        c.hover_moved.connect(lambda x, y: got.append((x, y)))
        self._send_move(c.viewport(), 30, 40)
        self.assertTrue(got, "hover_moved 应在鼠标移动时发出")
        self.assertEqual(got[-1], (30, 40))

    def _send_move(self, widget, x, y, buttons=0):
        """手工投递 MouseMove（QTest.mouseMove 在多窗口/offscreen 下
        不可靠：存在第二个未关闭窗口时不投递事件）。"""
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        ev = QMouseEvent(QEvent.Type.MouseMove, QPointF(x, y), QPointF(x, y),
                         Qt.MouseButton.NoButton,
                         Qt.MouseButton(buttons),
                         Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(widget, ev)

    def test_painter_hook_renders_in_viewport_coords(self):
        from PyQt6.QtCore import QPointF
        from PyQt6.QtGui import QColor, QTransform
        from PyQt6.QtCore import QRectF
        c = self._canvas()

        def cb(painter, rect, canvas):
            painter.save()
            painter.setWorldTransform(QTransform())
            painter.fillRect(QRectF(10, 10, 50, 50), QColor(255, 0, 0))
            painter.restore()

        c.add_painter(cb)
        img = c.grab().toImage()
        col = img.pixelColor(35, 35)
        self.assertEqual((col.red(), col.green(), col.blue()), (255, 0, 0))

    def test_painter_hook_runs_without_borders(self):
        # 钩子与矢量边界开关无关（OOB 无边界数据也必须绘制）
        c = self._canvas()
        calls = []
        c.add_painter(lambda p, r, cv: calls.append(1))
        c.grab()
        self.assertEqual(len(calls), 1)

    def test_image_pos_accepts_qpointf(self):
        """回归：PyQt6 event.position() 返回 QPointF，mapToScene 需要 QPoint。"""
        from PyQt6.QtCore import QPointF
        c = self._canvas()
        x, y = c._image_pos(QPointF(0.0, 0.0))
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)

    def test_province_clicked_in_point_mode(self):
        """回归：点选模式点击地块应发出 province_clicked（QPointF 事件）。"""
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        from map_canvas import MODE_POINT
        c = self._canvas()
        c.set_mode(MODE_POINT)
        c.centerOn(2, 2)
        self.app.processEvents()
        got = []
        c.province_clicked.connect(lambda pid, x, y: got.append(pid))
        QTest.mouseClick(
            c.viewport(), Qt.MouseButton.LeftButton,
            pos=QPoint(c.viewport().width() // 2,
                       c.viewport().height() // 2))
        self.assertEqual(len(got), 1, "点选模式点击应发出 province_clicked")
        self.assertIn(got[0], (1, 2), "8x8 地图中心点击应命中某个地块")

    # ------------------------------------------------------ 手型合并点选语义

    def _pan_canvas(self):
        c = self._canvas()
        c.centerOn(2, 2)
        self.app.processEvents()
        return c

    def test_pan_click_reports_province(self):
        """合并：手型模式单击应报告地块（原点选语义并入）。"""
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        c = self._pan_canvas()
        got = []
        c.province_clicked.connect(lambda pid, x, y: got.append(pid))
        QTest.mouseClick(
            c.viewport(), Qt.MouseButton.LeftButton,
            pos=QPoint(c.viewport().width() // 2,
                       c.viewport().height() // 2))
        self.assertEqual(len(got), 1, "手型单击应报告地块")
        self.assertIn(got[0], (1, 2))

    def test_pan_drag_no_report(self):
        """合并：手型拖拽平移不应报告地块（近距单击检测区分）。"""
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        c = self._pan_canvas()
        got_click, got_left = [], []
        c.province_clicked.connect(lambda pid, x, y: got_click.append(pid))
        c.left_clicked.connect(lambda x, y: got_left.append((x, y)))
        vp = c.viewport()
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, pos=QPoint(190, 140))
        QTest.mouseMove(vp, QPoint(210, 160))      # 超出近距阈值
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton,
                           pos=QPoint(210, 160))
        self.assertEqual(got_click, [], "拖拽不应报告地块")
        self.assertEqual(got_left, [], "拖拽不应触发 left_clicked")

    def test_pan_hover_reports(self):
        """合并：手型模式悬停应报告地块（原悬停语义并入）。"""
        c = self._pan_canvas()
        got = []
        c.province_hovered.connect(lambda pid: got.append(pid))
        self._send_move(c.viewport(), c.viewport().width() // 2,
                        c.viewport().height() // 2)
        self.assertTrue(got, "手型悬停应报告地块")
        self.assertIn(got[-1], (1, 2))

    def test_pan_drag_no_hover(self):
        """合并：手型拖拽平移中不报告悬停（QMouseEvent 带按键状态）。"""
        from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtTest import QTest
        c = self._pan_canvas()
        got = []
        c.province_hovered.connect(lambda pid: got.append(pid))
        vp = c.viewport()
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, pos=QPoint(190, 140))
        ev = QMouseEvent(QEvent.Type.MouseMove, QPointF(210, 160),
                         QPointF(210, 160), Qt.MouseButton.NoButton,
                         Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(vp, ev)
        self.assertEqual(got, [], "拖拽中不应报告悬停")
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton,
                           pos=QPoint(210, 160))

    # ------------------------------------------------------ 目标省份高亮层

    def test_hover_highlight_shows_when_enabled(self):
        """开启后悬停：目标省份醒目高亮（青色层）。"""
        c = self._pan_canvas()
        c.set_hover_highlight_enabled(True)
        self._send_move(c.viewport(), 200, 150)   # 视口中心 = 场景 (2,2)
        self.assertTrue(c.hover_item.isVisible(), "悬停目标省应高亮")
        self.assertIn(c._hover_pid, (1, 2))
        # 直接读 hover 覆盖层 pixmap（避开 grab 边框/白边偏移）：
        # 内部 = 青色半透明（蓝>红），边缘 = 白色不透明
        pm = c.hover_item.pixmap()
        self.assertFalse(pm.isNull())
        g = pm.toImage()
        cx, cy = g.width() // 2, g.height() // 2
        c_in = g.pixelColor(cx, cy)
        self.assertGreater(c_in.blue(), c_in.red(),
                           "悬停高亮内部应为青色系（蓝>红）")
        c_ed = g.pixelColor(0, g.height() // 2)
        self.assertEqual(c_ed.alpha(), 255,
                         "悬停高亮边缘应为白色不透明描边")

    def test_hover_highlight_hidden_by_default(self):
        """默认关闭：悬停不高亮（其他使用方不受影响）。"""
        c = self._pan_canvas()
        self._send_move(c.viewport(), 200, 150)
        self.assertFalse(c.hover_item.isVisible())
        self.assertEqual(c._hover_pid, 0)

    def test_hover_highlight_clears_on_blank(self):
        """悬停到地图外：目标省高亮清除。"""
        c = self._pan_canvas()
        c.set_hover_highlight_enabled(True)
        self._send_move(c.viewport(), 200, 150)
        self.assertTrue(c.hover_item.isVisible())
        self._send_move(c.viewport(), 5, 5)      # 场景 (-195,-145) 地图外
        self.assertFalse(c.hover_item.isVisible())
        self.assertEqual(c._hover_pid, 0)

    def test_rect_drag_accepts_qpointf_events(self):
        """回归：框选模式的 press/move/release 使用 QPointF 不应抛 TypeError。"""
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from map_canvas import MODE_RECT
        c = self._canvas()
        c.set_mode(MODE_RECT)
        pos = QPointF(50.0, 50.0)
        press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress, pos, pos,
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier)
        c.mousePressEvent(press)
        self.assertIsNotNone(c._drag_origin, "框选按下后应记录拖拽起点")
        move = QMouseEvent(
            QMouseEvent.Type.MouseMove, QPointF(120.0, 100.0),
            QPointF(120.0, 100.0), Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        c.mouseMoveEvent(move)      # 不应抛 TypeError
        release = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease, QPointF(120.0, 100.0),
            QPointF(120.0, 100.0), Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        c.mouseReleaseEvent(release)  # 不应抛 TypeError


class OobMapEditorSmokeTest(unittest.TestCase):
    """OobMapEditor（MapCanvas 版）offscreen 冒烟：打开/渲染/放置流程。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_map(self):
        from PyQt6.QtGui import QColor, QImage
        from map_loader import MapData
        mod = _mkdtemp("dsh_oob_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "map"), exist_ok=True)
        img = QImage(8, 8, QImage.Format.Format_RGB888)
        for y in range(8):
            for x in range(8):
                pid = 1 if x < 4 else 2
                img.setPixelColor(x, y, QColor(
                    (pid * 10) % 256, (pid * 20) % 256, (pid * 30) % 256))
        img.save(os.path.join(mod, "map", "provinces.bmp"), "BMP")
        with open(os.path.join(mod, "map", "definition.csv"), "w",
                  encoding="utf-8") as f:
            f.write("id;R;G;B;type;coastal;terrain;region\n")
            f.write("1;10;20;30;land;false;plains;1\n")
            f.write("2;20;40;60;land;false;plains;1\n")
        return mod, MapData(mod)

    def _stub_oob(self):
        class Tpl:
            name = "infantry_tpl"
            regiments = [("infantry",)]

        class Placement:
            def __init__(self, name, location, division_template,
                         start_experience_factor=None):
                self.name = name
                self.location = location
                self.division_template = division_template
                self.start_experience_factor = start_experience_factor

        class StubOob:
            file_path = "stub.oob"

            def __init__(self):
                self.templates = [Tpl()]
                self.placements = []
                self.modified = False

            def add_placement(self, p):
                self.placements.append(p)

            def remove_placement(self, p):
                self.placements.remove(p)

            def find_template(self, name):
                for t in self.templates:
                    if t.name == name:
                        return t
                return None

            def mark_units_modified(self):
                self.modified = True

            def save(self):
                pass

        return StubOob()

    def test_open_render_and_place(self):
        from unittest.mock import patch
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        from oob_map_editor import OobMapEditor
        mod, md = self._make_map()
        oob = self._stub_oob()
        dlg = OobMapEditor(oob, mod_path=mod, hoi4_path="")
        dlg.show()
        self.app.processEvents()
        img = dlg.canvas.grab().toImage()
        self.assertFalse(img.isNull(), "地图画布应可渲染")
        # 放置模式 + 点击陆地（场景中心 pid1）
        dlg.place_btn.setChecked(True)
        dlg.canvas.centerOn(2, 2)
        self.app.processEvents()
        with patch("oob_map_editor.QInputDialog.getText",
                   return_value=("测试师", True)):
            QTest.mouseClick(dlg.canvas.viewport(),
                             Qt.MouseButton.LeftButton,
                             pos=QPoint(dlg.canvas.viewport().width() // 2,
                                        dlg.canvas.viewport().height() // 2))
        self.app.processEvents()
        self.assertEqual(len(oob.placements), 1, "点击陆地应放置一支部队")
        self.assertEqual(oob.placements[0].name, "测试师")
        self.assertEqual(oob.placements[0].division_template, "infantry_tpl")
        self.assertEqual(len(dlg.counters), 1, "放置后应聚合出 1 个兵牌")
        # 兵牌绘制路径（drawPixmap QPointF 重载）必须能渲染
        img2 = dlg.canvas.grab().toImage()
        self.assertFalse(img2.isNull())
        dlg.close()


class OverlayRulesTest(unittest.TestCase):
    """overlay_rules 规则分层 + delta 增量报告契约。"""

    def _setup(self):
        mod = _mkdtemp("dsh_ovl_mod_")
        game = _mkdtemp("dsh_ovl_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        for base in (mod, game):
            os.makedirs(os.path.join(base, "common", "decisions"),
                        exist_ok=True)
        return mod, game

    def test_classify_kinds(self):
        from overlay_rules import classify_override
        mod, game = self._setup()
        # identical（字节一致）
        for base in (mod, game):
            with open(os.path.join(base, "common", "decisions", "a.txt"),
                      "w", encoding="utf-8") as f:
                f.write("x = 1\n")
        e1 = classify_override("common/decisions/a.txt",
                               os.path.join(mod, "common", "decisions",
                                            "a.txt"),
                               os.path.join(game, "common", "decisions",
                                            "a.txt"))
        self.assertEqual(e1["kind"], "identical")
        self.assertEqual(e1["quality"], "direct_copy")
        # override（内容不同 + 行级增量）
        with open(os.path.join(mod, "common", "decisions", "a.txt"),
                  "w", encoding="utf-8") as f:
            f.write("x = 1\ny = 2\n")
        e2 = classify_override("common/decisions/a.txt",
                               os.path.join(mod, "common", "decisions",
                                            "a.txt"),
                               os.path.join(game, "common", "decisions",
                                            "a.txt"))
        self.assertEqual(e2["kind"], "override")
        self.assertEqual(e2["delta"]["added"], 1)
        # new（游戏无对应文件）
        new_abs = os.path.join(mod, "common", "decisions", "new.txt")
        with open(new_abs, "w", encoding="utf-8") as f:
            f.write("n = 1\n")
        e3 = classify_override("common/decisions/new.txt", new_abs, None)
        self.assertEqual(e3["kind"], "new")

    def test_quality_grading(self):
        from overlay_rules import _quality_of
        self.assertEqual(_quality_of("identical", 10, "a", "a"),
                         "direct_copy")
        self.assertEqual(_quality_of("new", 10, None, "x"), "manual_reviewed")
        # 高度相似 → approx（9 行相同 + 1 行新增 → ratio 0.947）
        game9 = "".join("line%d = %d\n" % (i, i) for i in range(9))
        mod10 = game9 + "extra = 1\n"
        self.assertEqual(_quality_of("override", 100, game9, mod10),
                         "approx")
        # 大体积低相似 → blocker
        big_new = "x = 1\n" * 20000
        self.assertEqual(_quality_of("override", 200 * 1024,
                                     "a = 1\n" * 100, big_new), "blocker")

    def test_build_report_and_write(self):
        from overlay_rules import (build_override_report,
                                   write_override_report)
        mod, game = self._setup()
        with open(os.path.join(game, "common", "decisions", "g.txt"),
                  "w", encoding="utf-8") as f:
            f.write("g = 1\n")
        with open(os.path.join(mod, "common", "decisions", "g.txt"),
                  "w", encoding="utf-8") as f:
            f.write("g = 2\nm = 3\n")
        os.makedirs(os.path.join(mod, "events"), exist_ok=True)
        with open(os.path.join(mod, "events", "e.txt"), "w",
                  encoding="utf-8") as f:
            f.write("e = {}\n")
        r = build_override_report(mod, game)
        rels = [e["rel"] for e in r["files"]]
        self.assertIn("common/decisions/g.txt", rels)
        self.assertIn("events/e.txt", rels)
        self.assertEqual(r["stats"]["new"], 1)
        self.assertEqual(r["stats"]["override"], 1)
        # 顶层非内容文件不纳入
        with open(os.path.join(mod, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("n")
        r2 = build_override_report(mod, game)
        self.assertFalse(any(e["rel"] == "notes.txt" for e in r2["files"]))
        # 导出 JSON（原子写）
        out = os.path.join(mod, "report.json")
        write_override_report(mod, game, out)
        self.assertTrue(os.path.isfile(out))
        import json
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["stats"]["total"], 2)

    def test_rules_resolve_priority(self):
        from overlay_rules import OverlayRules
        rules = OverlayRules.load()
        layer, quality = rules.resolve("common/decisions/a.txt")
        self.assertEqual(layer.source, "mod")
        self.assertEqual(quality, "manual_reviewed")
        # 排除模式（*.bak）→ 回落只读层
        layer2, _q2 = rules.resolve("common/decisions/a.bak")
        self.assertEqual(layer2.source, "vanilla")


class IconManifestTest(unittest.TestCase):
    """icon_manifest 图标库清单契约。"""

    def _setup_gfx(self):
        from PIL import Image
        import numpy as np
        mod = _mkdtemp("dsh_im_mod_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        g = os.path.join(mod, "gfx", "interface")
        os.makedirs(g)
        with open(os.path.join(g, "icons.gfx"), "w", encoding="utf-8") as f:
            f.write('spriteType = { name = "GFX_ok" texturefile = '
                    '"gfx/interface/t.dds" }\n')
            f.write('spriteType = { name = "GFX_missing" texturefile = '
                    '"gfx/interface/nope.dds" }\n')
            f.write('spriteType = { name = "GFX_notexture" }\n')
        Image.fromarray(np.zeros((16, 16, 4), np.uint8)).save(
            os.path.join(g, "t.dds"))
        return mod

    def test_build_and_query(self):
        from icon_manifest import build_icon_manifest, IconManifest
        mod = self._setup_gfx()
        m = build_icon_manifest(mod, "")
        self.assertEqual(m["stats"]["total"], 2)
        im = IconManifest(m["entries"])
        e = im.get("GFX_ok")
        self.assertIsNotNone(e)
        self.assertEqual(e["missing"], False)
        self.assertEqual(e["size"], [16, 16])
        self.assertEqual(e["source"], "mod")
        self.assertTrue(im.get("GFX_missing")["missing"])
        self.assertIsNone(im.get("GFX_notexture"))
        self.assertEqual(len(im.search("GFX_")), 2)

    def test_vanilla_fallback_source(self):
        from PIL import Image
        import numpy as np
        from icon_manifest import build_icon_manifest
        mod = _mkdtemp("dsh_im_mod2_")
        game = _mkdtemp("dsh_im_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "gfx", "interface"))
        with open(os.path.join(game, "gfx", "interface", "v.gfx"),
                  "w", encoding="utf-8") as f:
            f.write('spriteType = { name = "GFX_van" texturefile = '
                    '"gfx/interface/v.dds" }\n')
        Image.fromarray(np.zeros((8, 8, 4), np.uint8)).save(
            os.path.join(game, "gfx", "interface", "v.dds"))
        m = build_icon_manifest(mod, game)
        e = next(x for x in m["entries"] if x["name"] == "GFX_van")
        self.assertEqual(e["source"], "vanilla")
        self.assertEqual(m["stats"]["sources"], {"vanilla": 1})

    def test_write_manifest(self):
        from icon_manifest import write_icon_manifest
        mod = self._setup_gfx()
        out = os.path.join(mod, "icon_manifest.json")
        write_icon_manifest(mod, "", out)
        self.assertTrue(os.path.isfile(out))
        import json
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["stats"]["total"], 2)
        self.assertEqual(len(data["entries"]), 2)


class UnitCounterLibraryTest(unittest.TestCase):
    """unit_counter_library 标牌库提取/加载契约。"""

    def _setup_game(self):
        from PIL import Image
        import numpy as np
        game = _mkdtemp("dsh_ucl_game_")
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        d1 = os.path.join(game, "gfx", "interface", "counters",
                          "divisions_small")
        d2 = os.path.join(game, "gfx", "interface", "counters",
                          "air_small")
        os.makedirs(d1)
        os.makedirs(d2)
        Image.fromarray(np.zeros((32, 32, 4), np.uint8)).save(
            os.path.join(d1, "onmap_infantry.dds"))
        Image.fromarray(np.zeros((24, 24, 4), np.uint8)).save(
            os.path.join(d2, "onmap_fighter.dds"))
        return game

    def test_import_and_load(self):
        from unit_counter_library import (import_unit_counter_library,
                                          UnitCounterLibrary)
        game = self._setup_game()
        out = _mkdtemp("dsh_ucl_out_")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        r = import_unit_counter_library(game, out)
        self.assertEqual(r["total"], 2)
        self.assertEqual(r["skipped"], 0)
        self.assertEqual(sorted(r["categories"]),
                         ["air_small", "divisions_small"])
        lib = UnitCounterLibrary(out)
        self.assertTrue(lib.is_ready)
        self.assertEqual(sorted(lib.names),
                         ["onmap_fighter", "onmap_infantry"])
        e = lib.get("onmap_infantry")
        self.assertEqual(e["category"], "divisions_small")
        self.assertEqual(e["size"], [32, 32])
        self.assertTrue(os.path.isfile(lib.abs_path(e)))
        # 类别过滤
        self.assertEqual([x["name"] for x in lib.entries_in("air_small")],
                         ["onmap_fighter"])

    def test_empty_library_ready_false(self):
        from unit_counter_library import UnitCounterLibrary
        out = _mkdtemp("dsh_ucl_empty_")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        lib = UnitCounterLibrary(out)
        self.assertFalse(lib.is_ready)
        self.assertEqual(lib.names, [])


class SubUnitStatsTest(unittest.TestCase):
    """编制属性解析与汇总（基础值估算）：load_sub_units 扩展 /
    load_equipment_stats / division_stats。"""

    def test_load_sub_units_extended_fields(self):
        """营属性字段/need/terrain 解析。"""
        from oob_loader import load_sub_units
        mod = _mkdtemp("dsh_sub_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "units"), exist_ok=True)
        with open(os.path.join(mod, "common", "units", "infantry.txt"),
                  "w", encoding="utf-8") as f:
            f.write('sub_units = {\n'
                    '\tinfantry = {\n'
                    '\t\tabbreviation = "INF"\n'
                    '\t\tgroup = infantry\n'
                    '\t\tcombat_width = 2\n'
                    '\t\tmax_strength = 25\n'
                    '\t\tmax_organisation = 60\n'
                    '\t\tmaximum_speed = 4.0\n'
                    '\t\tmanpower = 1000\n'
                    '\t\tsuppression = 1.5\n'
                    '\t\tneed = { infantry_equipment = 100 support_equipment = 10 }\n'
                    '\t\tforest = { movement = 0.2 }\n'
                    '\t\tdesert = { movement = -0.1 }\n'
                    '\t}\n'
                    '}\n')
        sub = load_sub_units(mod, "")
        inf = sub["infantry"]
        self.assertEqual(inf["abbreviation"], "INF")
        self.assertEqual(inf["combat_width"], 2.0)
        self.assertEqual(inf["maximum_speed"], 4.0)
        self.assertEqual(inf["manpower"], 1000.0)
        self.assertEqual(inf["need"], {"infantry_equipment": 100.0,
                                       "support_equipment": 10.0})
        self.assertEqual(inf["terrain"], {"forest": 0.2, "desert": -0.1})
        self.assertIsNone(inf["soft_attack"], "缺失字段应为 None")

    def test_division_stats_math(self):
        """汇总数学：宽度 Σ / 速度 min / 人力 Σ / org 平均 / 攻击营字段优先。"""
        from oob_loader import division_stats
        from oob_loader import DivisionTemplate
        sub = {
            "infantry": {"combat_width": 2.0, "maximum_speed": 4.0,
                         "manpower": 1000.0, "max_organisation": 60.0,
                         "max_strength": 25.0, "suppression": 1.5,
                         "soft_attack": 6.0, "defense": 22.0,
                         "need": {"infantry_equipment": 100.0},
                         "terrain": {"forest": 0.2}},
            "motorized": {"combat_width": 2.0, "maximum_speed": 12.0,
                          "manpower": 1000.0, "max_organisation": 60.0,
                          "max_strength": 25.0, "soft_attack": 7.0,
                          "need": {"motorized_equipment": 100.0},
                          "terrain": {"forest": -0.1}},
            "engineer": {"combat_width": 1.0, "maximum_speed": 4.0,
                         "manpower": 100.0, "max_organisation": 60.0,
                         "max_strength": 25.0, "support": True,
                         "need": {"support_equipment": 50.0}},
        }
        tpl = DivisionTemplate("T", regiments=[("infantry", 0, 0),
                                               ("motorized", 0, 1)],
                               support=[("engineer", 0, 0)])
        st = division_stats(tpl, sub, {})
        self.assertEqual(st["width"], 5.0, "2+2+1 战斗宽度")
        self.assertEqual(st["manpower"], 2100)
        self.assertEqual(st["speed"], 4.0, "取最慢")
        self.assertAlmostEqual(st["org"], 60.0)
        self.assertEqual(st["soft"], 13.0, "营字段直接汇总")
        self.assertEqual(st["defense"], 22.0, "缺失字段回退装备 → 无则 0")
        self.assertEqual(st["equipment"],
                         {"infantry_equipment": 100.0,
                          "motorized_equipment": 100.0,
                          "support_equipment": 50.0})
        self.assertAlmostEqual(st["terrain"]["forest"], 0.05, places=6,
                               msg="地形 movement 取平均 (0.2-0.1)/2")
        self.assertEqual(st["counts"], {"battalions": 2, "support": 1})

    def test_division_stats_equip_fallback(self):
        """攻击字段缺失 → 主装备基础值回退（need 类别前缀 → 变体匹配）。"""
        from oob_loader import division_stats, DivisionTemplate
        sub = {"infantry": {"combat_width": 2.0,
                            "need": {"infantry_equipment": 100.0}}}
        eq = {"infantry_equipment_0": {"soft_attack": 6.0, "defense": 22.0},
              "infantry_equipment_1": {"soft_attack": 8.0}}
        tpl = DivisionTemplate("T", regiments=[("infantry", 0, 0)])
        st = division_stats(tpl, sub, eq)
        self.assertEqual(st["soft"], 6.0, "前缀匹配应取 _0 基础变体")
        self.assertEqual(st["defense"], 22.0)

    def test_load_equipment_stats_nested(self):
        """equipments = {} 包裹与直接顶层两种写法都能解析。"""
        from oob_loader import load_equipment_stats
        mod = _mkdtemp("dsh_eq_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "units", "equipment"),
                    exist_ok=True)
        with open(os.path.join(mod, "common", "units", "equipment",
                               "infantry.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tinfantry_equipment_1 = {\n'
                    '\t\tsoft_attack = 6\n\t\tdefense = 22\n'
                    '\t\tbreakthrough = 3\n\t}\n'
                    '}\n')
        with open(os.path.join(mod, "common", "units", "equipment",
                               "support.txt"), "w", encoding="utf-8") as f:
            f.write('support_equipment_0 = {\n\treliability = 0.8\n}\n')
        eq = load_equipment_stats(mod, "")
        self.assertEqual(eq["infantry_equipment_1"]["soft_attack"], 6.0)
        self.assertEqual(eq["support_equipment_0"]["reliability"], 0.8)
        # 缓存：再查同一路径直接命中
        self.assertIs(load_equipment_stats(mod, ""), eq)


class DivisionEditorSmokeTest(unittest.TestCase):
    """DivisionEditor v2 offscreen 冒烟：顶部下拉 / 数据面板 / 地形矩阵 / 重置。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        """临时 OOB 文件 + 构造 sub_units（带属性字段）。"""
        from oob_loader import OobFile
        mod = _mkdtemp("dsh_dived_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        content = ('division_template = {\n'
                   '\tname = "Alpha Div"\n'
                   '\tregiments = {\n'
                   '\t\tinfantry = { x = 0 y = 0 }\n'
                   '\t\tinfantry = { x = 0 y = 1 }\n'
                   '\t\tartillery = { x = 1 y = 0 }\n'
                   '\t}\n'
                   '\tsupport = {\n'
                   '\t\tengineer = { x = 0 y = 0 }\n'
                   '\t}\n'
                   '}\n'
                   'division_template = {\n'
                   '\tname = "Beta Div"\n'
                   '\tregiments = {\n'
                   '\t\tmotorized = { x = 0 y = 0 }\n'
                   '\t}\n'
                   '}\n')
        path = os.path.join(mod, "test_oob.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        sub = {
            "infantry": {"abbreviation": "INF", "group": "infantry",
                         "combat_width": 2.0, "manpower": 1000.0,
                         "max_organisation": 60.0, "max_strength": 25.0,
                         "maximum_speed": 4.0, "suppression": 1.5,
                         "weight": 0.5, "supply_consumption": 0.06,
                         "training_time": 90.0, "soft_attack": 6.0,
                         "defense": 22.0,
                         "need": {"infantry_equipment": 100.0},
                         "terrain": {"forest": 0.1, "desert": -0.2}},
            "artillery": {"abbreviation": "ART", "group": "combat_support",
                          "combat_width": 3.0, "manpower": 300.0,
                          "max_organisation": 30.0, "max_strength": 20.0,
                          "maximum_speed": 4.0, "soft_attack": 20.0,
                          "need": {"artillery_equipment": 36.0}},
            "motorized": {"abbreviation": "MOT", "group": "mobile",
                          "combat_width": 2.0, "manpower": 1000.0,
                          "max_organisation": 60.0, "max_strength": 25.0,
                          "maximum_speed": 12.0, "soft_attack": 7.0,
                          "need": {"motorized_equipment": 100.0}},
            "engineer": {"abbreviation": "ENG", "group": "support",
                         "support": True, "combat_width": 1.0,
                         "manpower": 100.0, "max_organisation": 60.0,
                         "max_strength": 25.0, "maximum_speed": 4.0,
                         "need": {"support_equipment": 50.0}},
        }
        return mod, OobFile(path), sub

    def test_build_combo_and_stats(self):
        """顶部下拉 + 数据面板 + 地形矩阵 + 装备汇总。"""
        from division_editor import DivisionEditor
        mod, oob, sub = self._make_env()
        dlg = DivisionEditor(oob, sub, {}, "", "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.combo.count(), 2)
        self.assertEqual(dlg.current.name, "Alpha Div")
        self.assertEqual(dlg._stat_labels["width"].text(), "8",
                         "2×2 步兵 + 3 火炮 + 1 工兵 = 8 宽度")
        self.assertEqual(dlg._stat_labels["manpower"].text(), "2400")
        self.assertEqual(dlg._stat_labels["speed"].text(), "4 km/h")
        self.assertEqual(dlg._stat_labels["soft"].text(), "32",
                         "6+6+20 营字段汇总")
        # 地形徽章：8 个、desert 为 -20%
        self.assertEqual(len(dlg._terrain_labels), 8)
        self.assertIn("-20%", dlg._terrain_labels["desert"][0].text())
        # 装备汇总
        self.assertIn("infantry_equipment", dlg._equip_text.text())
        self.assertIn("3 种 · 合计 286 件", dlg.equip_summary.text())
        dlg.close()

    def test_combo_switch_updates_stats(self):
        """下拉切换模板 → 数据面板刷新。"""
        from division_editor import DivisionEditor
        mod, oob, sub = self._make_env()
        dlg = DivisionEditor(oob, sub, {}, "", "")
        dlg.show()
        self.app.processEvents()
        dlg.combo.setCurrentIndex(1)
        self.app.processEvents()
        self.assertEqual(dlg.current.name, "Beta Div")
        self.assertEqual(dlg._stat_labels["width"].text(), "2")
        self.assertEqual(dlg._stat_labels["manpower"].text(), "1000")
        dlg.close()

    def test_remove_updates_stats(self):
        """移除营 → 面板数值即时更新。"""
        from division_editor import DivisionEditor
        mod, oob, sub = self._make_env()
        dlg = DivisionEditor(oob, sub, {}, "", "")
        dlg.show()
        self.app.processEvents()
        tpl = dlg.current
        tpl.regiments = [r for r in tpl.regiments
                         if not (r[1] == 1 and r[2] == 0)]
        dlg._rebuild_editor(tpl)
        self.app.processEvents()
        self.assertEqual(dlg._stat_labels["width"].text(), "5")
        self.assertEqual(dlg._stat_labels["soft"].text(), "12")
        dlg.close()

    def test_reset_restores_template(self):
        """⟲ 重置：丢弃未保存修改，从文件原始内容恢复。"""
        from division_editor import DivisionEditor
        mod, oob, sub = self._make_env()
        dlg = DivisionEditor(oob, sub, {}, "", "")
        dlg.show()
        self.app.processEvents()
        tpl = dlg.current
        tpl.regiments = [r for r in tpl.regiments
                         if not (r[1] == 1 and r[2] == 0)]
        dlg._rebuild_editor(tpl)
        self.assertEqual(len(dlg.current.regiments), 2)
        dlg._reset_current()
        self.app.processEvents()
        self.assertEqual(len(dlg.current.regiments), 3, "重置后恢复 3 营")
        self.assertEqual(dlg._stat_labels["width"].text(), "8")
        dlg.close()


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
                    '\tupgrades = {\n'
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
        """apply/insert/remove/rename 块级写回。"""
        from ship_design import apply_variant_upgrades, insert_variant, \
            remove_variant, rename_variant
        content = ('TAG = {\n'
                   '\tcreate_equipment_variant = {\n'
                   '\t\tname = "X"\n'
                   '\t\ttype = ship_hull_light_1\n'
                   '\t\tupgrades = {\n'
                   '\t\t\tfixed_ship_battery_slot = ship_light_battery_1\n'
                   '\t\t}\n'
                   '\t}\n'
                   '}\n')
        new = apply_variant_upgrades(
            content, "X",
            {"fixed_ship_battery_slot": "ship_light_battery_2",
             "fixed_ship_engine_slot": "light_ship_engine_1"})
        self.assertIn("ship_light_battery_2", new)
        self.assertNotIn("ship_light_battery_1", new)
        self.assertIn("fixed_ship_engine_slot = light_ship_engine_1", new)
        self.assertEqual(apply_variant_upgrades(content, "NoSuch", {}), None)
        # 无 upgrades 块的插入
        plain = ('TAG = {\n\tcreate_equipment_variant = {\n'
                 '\t\tname = "Y"\n\t\ttype = ship_hull_light_1\n\t}\n}\n')
        new = apply_variant_upgrades(plain, "Y",
                                     {"fixed_ship_battery_slot": "slb_1"})
        self.assertIn("upgrades = {", new)
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
                    '\tupgrades = {\n'
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


class DesignTemplateTest(unittest.TestCase):
    """设计模板：保存/列表/加载 + 与普通模板搜索器隔离。"""

    def _clean_root(self):
        import design_template
        root = design_template.design_templates_root()
        shutil.rmtree(root, ignore_errors=True)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        return root

    def test_save_list_load(self):
        """保存/列表/加载 roundtrip。"""
        import design_template as dt
        self._clean_root()
        p = dt.save_design_template("ship", "测试驱逐", "content A")
        self.assertTrue(os.path.isfile(p))
        p2 = dt.save_design_template("ship", "测试驱逐", "content B")
        self.assertNotEqual(p, p2, "重名应自动加序号")
        names = [t["name"] for t in dt.list_design_templates("ship")]
        self.assertIn("测试驱逐", names)
        self.assertIn("测试驱逐_1", names)
        self.assertEqual(dt.load_design_template("ship", "测试驱逐"),
                         "content A")
        self.assertEqual(dt.load_design_template("ship", "测试驱逐_1"),
                         "content B")

    def test_kind_isolation(self):
        """不同设计器种类目录互不干扰。"""
        import design_template as dt
        self._clean_root()
        dt.save_design_template("plane", "He 111", "plane content")
        self.assertEqual(len(dt.list_design_templates("plane")), 1)
        self.assertEqual(dt.list_design_templates("tank"), [])
        self.assertIsNone(dt.load_design_template("tank", "He 111"))

    def test_not_found_by_regular_template_search(self):
        """普通模板搜索器（TemplateScheduler 扫 templates/）搜不到设计模板。"""
        import design_template as dt
        from template_scheduler import TemplateScheduler
        self._clean_root()
        dt.save_design_template("tank", "Leichttraktor", "tank content")
        sched = TemplateScheduler(
            templates_dir=os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "..", "templates"))
        hits = [r for r in sched.search_templates(keyword="Leichttraktor")
                if "Leichttraktor" in r["name"]]
        self.assertEqual(hits, [], "设计模板不应出现在普通模板搜索器结果中")


class DesignTemplateDialogSmokeTest(unittest.TestCase):
    """设计器「存为模板/从模板新建」offscreen 冒烟（以舰艇为例）。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from ship_design import _HULLS_CACHE, _MODULES_CACHE, _VARIANTS_CACHE
        import design_template as dt
        root = dt.design_templates_root()
        shutil.rmtree(root, ignore_errors=True)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        mod = _mkdtemp("dsh_tplship_")
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
                    '}\n')
        c_dir = os.path.join(mod, "history", "countries")
        os.makedirs(c_dir, exist_ok=True)
        with open(os.path.join(c_dir, "JAP - Japan.txt"),
                  "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Test Ship"\n'
                    '\ttype = ship_hull_light_1\n'
                    '\tupgrades = {\n'
                    '\t\tfixed_ship_battery_slot = ship_light_battery_1\n'
                    '\t}\n'
                    '}\n')
        _HULLS_CACHE.clear()
        _MODULES_CACHE.clear()
        _VARIANTS_CACHE.clear()
        return mod

    def test_save_as_template_roundtrip(self):
        """存为模板 → 文件存在；从模板新建 → 内存设计增加。"""
        from unittest.mock import patch
        import design_template as dt
        from ship_design_dialog import ShipDesignDialog
        mod = self._make_env()
        dlg = ShipDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        # 存为模板（patch QInputDialog.getText）
        with patch("PyQt6.QtWidgets.QInputDialog.getText",
                   return_value=("Tpl Ship", True)), \
                patch("ship_design_dialog.QMessageBox.information"), \
                patch("ship_design_dialog.QMessageBox.critical"):
            dlg._save_as_template()
        tpls = dt.list_design_templates("ship")
        self.assertEqual(len(tpls), 1)
        content = dt.load_design_template("ship", "Tpl Ship")
        self.assertIn("ship_hull_light_1", content)
        self.assertIn("ship_light_battery_1", content)
        # 从模板新建（patch QInputDialog.getItem 选择该模板）
        with patch("PyQt6.QtWidgets.QInputDialog.getItem",
                   return_value=("Tpl Ship", True)):
            dlg._new_from_template()
        self.app.processEvents()
        self.assertIn("Tpl Ship", dlg.variants["JAP"])
        self.assertEqual(dlg.current_name, "Tpl Ship")
        self.assertEqual(
            dlg.current_variant.get("modules", {}).get("fixed_ship_battery_slot"),
            "ship_light_battery_1")
        dlg.close()


class WorkbenchNofileCountryTest(unittest.TestCase):
    """无文件模式国家选择：纯选择不写文件 + 下方状态条展示当前国家。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        """临时 mod（空）+ game（含国家文件）。"""
        from workbench import WorkbenchDock
        mod = _mkdtemp("dsh_wbmod_")
        game = _mkdtemp("dsh_wbgame_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        os.makedirs(os.path.join(game, "history", "countries"), exist_ok=True)
        os.makedirs(os.path.join(game, "common", "country_tags"), exist_ok=True)
        with open(os.path.join(game, "common", "country_tags",
                               "00_countries.txt"), "w", encoding="utf-8") as f:
            f.write('GER = "countries/GER - Germany.txt"\n'
                    'JAP = "countries/JAP - Japan.txt"\n')
        with open(os.path.join(game, "history", "countries",
                               "GER - Germany.txt"), "w", encoding="utf-8") as f:
            f.write("capital = 1\n")
        with open(os.path.join(game, "history", "countries",
                               "JAP - Japan.txt"), "w", encoding="utf-8") as f:
            f.write("capital = 1\n")
        wb = WorkbenchDock(mod_path=mod)
        wb.set_nofile_mode(True)
        wb.show()
        self.app.processEvents()
        return mod, game, wb

    def _snapshot(self, root):
        """目录下文件相对路径 + 内容快照。"""
        snap = {}
        for root2, _dirs, files in os.walk(root):
            for fn in files:
                p = os.path.join(root2, fn)
                rel = os.path.relpath(p, root)
                with open(p, "rb") as f:
                    snap[rel] = f.read()
        return snap

    def test_pure_select_does_not_write_files(self):
        """🔍 选择国家只切换筛选，不产生/修改任何 mod 文件。"""
        from unittest.mock import patch
        mod, game, wb = self._make_env()
        before = self._snapshot(mod)
        # patch _game_path 返回临时 game；patch 选择 GER
        with patch.object(wb, "_game_path", return_value=game), \
                patch("PyQt6.QtWidgets.QInputDialog.getItem",
                      return_value=("GER  Germany", True)):
            wb._on_select_country()
        self.app.processEvents()
        self.assertEqual(wb.current_country(), "GER")
        self.assertIn("Germany", wb.country_label.text(),
                      "国家栏应显示国家名")
        self.assertEqual(self._snapshot(mod), before,
                         "纯选择不得修改 mod 内任何文件")

    def test_country_label_shows_name_and_all(self):
        """set_current_country 显示国家名；全部时显示「全部」。"""
        from unittest.mock import patch
        mod, game, wb = self._make_env()
        with patch.object(wb, "_game_path", return_value=game):
            wb.set_current_country("JAP")
        self.assertEqual(wb.current_country(), "JAP")
        self.assertIn("Japan", wb.country_label.text())
        wb.set_current_country("")
        self.assertEqual(wb.country_label.text(), "当前国家：全部")


class OobOpenDesignerTest(unittest.TestCase):
    """打开 OOB 文件 → 直接进入师编制设计器，顶部含地编/其他设计器入口。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_oob(self):
        mod = _mkdtemp("dsh_oobopen_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        path = os.path.join(mod, "test_oob.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write('division_template = {\n'
                    '\tname = "Test Div"\n'
                    '\tregiments = {\n'
                    '\t\tinfantry = { x = 0 y = 0 }\n'
                    '\t}\n'
                    '}\n')
        return mod, path

    def test_open_oob_directly_opens_division_editor(self):
        """open_oob_designer 返回师编制设计器并加载模板。"""
        from initial_oob_editor import open_oob_designer
        mod, path = self._make_oob()
        dlg = open_oob_designer(path, mod_path=mod, hoi4_path="")
        self.app.processEvents()
        self.assertEqual(dlg.windowTitle(), "师编制编辑器")
        self.assertEqual(dlg.combo.count(), 1)
        self.assertEqual(dlg.current.name, "Test Div")
        dlg.close()

    def test_division_editor_top_has_map_and_designers(self):
        """编制设计器顶部：地编按钮 + 设计器菜单（舰艇/飞机/坦克）。"""
        from division_editor import DivisionEditor
        from oob_loader import OobFile
        mod, path = self._make_oob()
        dlg = DivisionEditor(OobFile(path), {}, {}, mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.place_btn.text(), "🗺 地编（地图放置）…")
        self.assertEqual(dlg.design_btn.text(), "🛠 设计器 ▾")
        actions = [a.text() for a in dlg.design_btn.menu().actions()]
        self.assertIn("🚢 舰艇设计…", actions)
        self.assertIn("✈ 飞机设计…", actions)
        self.assertIn("🛡 坦克设计…", actions)
        dlg.close()


class OobFileModeOpenTest(unittest.TestCase):
    """非无文件模式（经典文件树/工作台文件模式）打开 OOB 文件 → 设计器路由。"""

    def test_open_tree_editor_routes_oob_to_designer(self):
        """工作台/经典共用的 _open_tree_editor 对 history/units 调用设计器工厂。"""
        from unittest.mock import patch, MagicMock
        from main_window import MyWindow
        fake = MagicMock()
        fake.settings = {"mod_path": "/tmp/mod", "HOI4_path": "/tmp/game"}
        with patch("initial_oob_editor.open_oob_designer") as m:
            MyWindow._open_tree_editor(
                fake, "/tmp/mod/history/units/test_oob.txt")
        m.assert_called_once()
        file_arg = m.call_args[0][0]
        self.assertTrue(file_arg.endswith("test_oob.txt"))
        self.assertEqual(m.call_args[1]["mod_path"], "/tmp/mod")

    def test_load_txt_pdx_routes_oob_to_designer(self):
        """经典文件树双击 load_txt_pdx_to_memory 对 OOB 文件调用设计器工厂。"""
        from unittest.mock import patch, MagicMock
        from main_window import MyWindow
        mod = _mkdtemp("dsh_oobroute_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        oob_dir = os.path.join(mod, "history", "units")
        os.makedirs(oob_dir, exist_ok=True)
        path = os.path.join(oob_dir, "test_oob.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write('division_template = {\n\tname = "X"\n}\n')
        fake = MagicMock()
        fake.settings = {"mod_path": mod, "HOI4_path": ""}
        with patch("main_window.parse_pdx_script",
                   return_value='division_template = {\n\tname = "X"\n}\n'), \
                patch("initial_oob_editor.open_oob_designer") as m:
            MyWindow.load_txt_pdx_to_memory(fake, path)
        m.assert_called_once()


class WorkbenchOobDoubleClickTest(unittest.TestCase):
    """双击初始部队文件必须弹设计器（generic_file_selected），不能只进实体画廊。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from workbench import WorkbenchDock
        mod = _mkdtemp("dsh_wboob_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "history", "units"), exist_ok=True)
        path = os.path.join(mod, "history", "units", "test_oob.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write('division_template = {\n\tname = "X"\n}\n')
        wb = WorkbenchDock(mod_path=mod)
        wb._current_type = "initial_oob"
        wb.show()
        self.app.processEvents()
        return wb, path

    def test_file_mode_double_click_opens_designer(self):
        """文件模式双击 OOB：走 generic_file_selected（→ 设计器），不进画廊。"""
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        wb, path = self._make_env()
        received = []
        gallery = []
        wb.generic_file_selected.connect(
            lambda fp, eid: received.append((fp, eid)))
        wb.entity_gallery_requested.connect(
            lambda t, fp: gallery.append((t, fp)))
        it = QListWidgetItem("test_oob")
        it.setData(Qt.ItemDataRole.UserRole, path)
        wb._on_file_double_clicked(it)
        self.assertEqual(len(received), 1, "应请求打开设计器")
        self.assertTrue(received[0][0].endswith("test_oob.txt"))
        self.assertEqual(gallery, [], "不得只展示实体画廊")

    def test_nofile_entity_double_click_opens_designer(self):
        """无文件模式双击 OOB 实体：同样走 generic_file_selected。"""
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        wb, path = self._make_env()
        wb.set_nofile_mode(True)
        received = []
        gallery = []
        wb.generic_file_selected.connect(
            lambda fp, eid: received.append((fp, eid)))
        wb.entity_gallery_nofile_requested.connect(
            lambda t, es: gallery.append((t, len(es))))
        it = QListWidgetItem("test_oob")
        it.setData(Qt.ItemDataRole.UserRole,
                   {"file": path, "key": "division_template"})
        wb._on_entity_double_clicked(it)
        self.assertEqual(len(received), 1)
        self.assertTrue(received[0][0].endswith("test_oob.txt"))
        self.assertEqual(received[0][1], "division_template")
        self.assertEqual(gallery, [])


class WorkbenchTypeListGroupTest(unittest.TestCase):
    """工作台类型列表：专门功能类型置顶，通用类型在分界线下方。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make(self):
        from workbench import WorkbenchDock
        mod = _mkdtemp("dsh_wbtypes_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        wb = WorkbenchDock(mod_path=mod)
        wb.show()
        self.app.processEvents()
        return wb

    def test_special_types_on_top_and_separator(self):
        """专门类型在顶部；分隔线不可选；其后为通用类型。"""
        from PyQt6.QtCore import Qt
        wb = self._make()
        keys = []
        for i in range(wb.type_list.count()):
            it = wb.type_list.item(i)
            keys.append((i, it.data(Qt.ItemDataRole.UserRole),
                         bool(it.flags() & Qt.ItemFlag.ItemIsSelectable)))
        self.assertEqual(
            [k for _i, k, _s in keys[:12]],
            ["focus", "tech", "initial_oob", "bop",
             "ai_strategy_plans", "ai_strategy", "ai_division", "ai_areas",
             "ai_equipment", "ai_faction_theaters", "ai_focuses", "ai_navy"])
        sep = keys[12]
        self.assertIsNone(sep[1], "分隔线无类型 data")
        self.assertFalse(sep[2], "分隔线不可选")
        self.assertIsNotNone(keys[13][1], "分隔线后应有通用类型")

    def test_clicking_separator_ignored(self):
        """点击分隔线不改变当前类型。"""
        from PyQt6.QtCore import Qt
        wb = self._make()
        wb._current_type = "focus"
        sep = wb.type_list.item(12)
        wb._on_type_clicked(sep)
        self.assertEqual(wb._current_type, "focus", "分隔线点击应被忽略")


class OobKindDetectTest(unittest.TestCase):
    """OOB 军种识别：陆军/海军/空军；打开文件自动拉起对应设计面板。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_detect_oob_kinds(self):
        """detect_oob_kinds 正确识别 division/ship/air_wings。"""
        from oob_loader import detect_oob_kinds
        self.assertEqual(detect_oob_kinds("division_template = {\n}\n"),
                         {"army": True, "navy": False, "air": False})
        self.assertEqual(
            detect_oob_kinds("units = {\n\tship = { name = \"S\" }\n}\n"),
            {"army": False, "navy": True, "air": False})
        self.assertEqual(
            detect_oob_kinds("units = {\n\tair_wing = { name = \"W\" }\n}\n"),
            {"army": False, "navy": False, "air": True})
        self.assertEqual(
            detect_oob_kinds("air_wings = {\n\t278 = {}\n}\n"),
            {"army": False, "navy": False, "air": True})
        self.assertEqual(
            detect_oob_kinds("units = {\n\tfleet = { task_force = {} }\n}\n"),
            {"army": False, "navy": True, "air": False})
        self.assertEqual(
            detect_oob_kinds("division = {\n}\nship = {\n}\nair_wings = {\n}\n"),
            {"army": True, "navy": True, "air": True})

    def _open_kind(self, content):
        from initial_oob_editor import open_oob_designer
        mod = _mkdtemp("dsh_oobkind_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "history", "units"), exist_ok=True)
        path = os.path.join(mod, "history", "units", "kind.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return open_oob_designer(path, mod_path=mod, hoi4_path="")

    def test_open_army_launches_division_editor(self):
        dlg = self._open_kind('division_template = {\n\tname = "A"\n}\n')
        self.app.processEvents()
        self.assertEqual(dlg.__class__.__name__, "DivisionEditor")
        dlg.close()

    def test_open_navy_launches_ship_designer(self):
        dlg = self._open_kind('units = {\n\tship = { name = "S" }\n}\n')
        self.app.processEvents()
        self.assertEqual(dlg.__class__.__name__, "ShipDesignDialog")
        dlg.close()

    def test_open_air_launches_plane_designer(self):
        dlg = self._open_kind('units = {\n\tair_wing = { name = "W" }\n}\n')
        self.app.processEvents()
        self.assertEqual(dlg.__class__.__name__, "PlaneDesignDialog")
        dlg.close()


class OobOtherContentDetectTest(unittest.TestCase):
    """OOB 其他内容检测：文件含未覆盖顶层块时，打开前让用户选择。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_oob(self, content):
        from initial_oob_editor import open_oob_designer
        mod = _mkdtemp("dsh_oobother_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "history", "units"), exist_ok=True)
        path = os.path.join(mod, "history", "units", "other.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return open_oob_designer, mod, path

    def test_detect_oob_other_content(self):
        from oob_loader import detect_oob_other_content
        self.assertEqual(
            detect_oob_other_content('division_template = {\n}\n'), [])
        self.assertEqual(
            detect_oob_other_content('air_wings = {\n}\n'), [])
        self.assertEqual(
            detect_oob_other_content(
                'division_template = {\n}\ninstant_effect = {\n}\n'),
            ["instant_effect"])
        self.assertEqual(
            detect_oob_other_content(
                'create_colonial_division_template = {\n\tsubject = COG\n}\n'),
            ["create_colonial_division_template"])

    def test_open_with_other_and_choose_designer(self):
        from unittest.mock import patch
        open_oob_designer, mod, path = self._make_oob(
            'division_template = {\n\tname = "A"\n}\n'
            'instant_effect = {\n\tadd_equipment_production = {}\n}\n')
        with patch("initial_oob_editor._ask_oob_open_mode",
                   return_value="designer"):
            dlg = open_oob_designer(path, mod_path=mod, hoi4_path="")
        self.app.processEvents()
        self.assertEqual(dlg.__class__.__name__, "DivisionEditor")
        dlg.close()

    def test_open_with_other_and_choose_tree(self):
        from unittest.mock import patch
        open_oob_designer, mod, path = self._make_oob(
            'division_template = {\n}\ninstant_effect = {\n}\n')
        with patch("initial_oob_editor._ask_oob_open_mode",
                   return_value="tree"):
            dlg = open_oob_designer(path, mod_path=mod, hoi4_path="")
        self.app.processEvents()
        self.assertEqual(dlg.__class__.__name__, "GenericTreeEditor")
        dlg.close()

    def test_open_with_other_and_cancel(self):
        from unittest.mock import patch
        open_oob_designer, mod, path = self._make_oob(
            'division_template = {\n}\ninstant_effect = {\n}\n')
        with patch("initial_oob_editor._ask_oob_open_mode",
                   return_value=None):
            result = open_oob_designer(path, mod_path=mod, hoi4_path="")
        self.assertIsNone(result)

    def test_open_with_other_and_choose_both(self):
        from unittest.mock import patch
        open_oob_designer, mod, path = self._make_oob(
            'division_template = {\n\tname = "A"\n}\n'
            'instant_effect = {\n}\n')
        with patch("initial_oob_editor._ask_oob_open_mode",
                   return_value="both"):
            result = open_oob_designer(path, mod_path=mod, hoi4_path="")
        self.app.processEvents()
        self.assertIsInstance(result, list)
        names = [getattr(x, "__class__", None).__name__ for x in result]
        self.assertIn("GenericTreeEditor", names)
        self.assertIn("DivisionEditor", names)
        for x in result:
            x.close()


class DynamicModifierTemplateTest(unittest.TestCase):
    """动态修正模板：模板系统可搜索到基础/项目模板，分类已接入搜索器。"""

    def test_search_returns_dynamic_modifier_templates(self):
        """TemplateScheduler 按「动态修正」类型返回基础(file)+项目(node)。"""
        from template_scheduler import TemplateScheduler
        sched = TemplateScheduler(
            templates_dir=os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "..", "templates"))
        hits = sched.search_templates(template_type="动态修正")
        names = {h["name"]: h["usage"] for h in hits}
        self.assertIn("基础模板", names)
        self.assertIn("项目模板", names)
        self.assertEqual(names["基础模板"], "file")
        self.assertEqual(names["项目模板"], "node")
        # 模板内容应包含动态修正关键字段
        base = next(h for h in hits if h["name"] == "基础模板")
        with open(base["filepath"], "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("remove_trigger", content)
        self.assertIn("attacker_modifier", content)
        self.assertIn("add_dynamic_modifier", content)

    def test_dialog_category_includes_dynamic_modifier(self):
        """模板搜索对话框分类含「动态修正」。"""
        from template_dialog import CATEGORIES
        self.assertIn(("动态修正", "动态修正"), CATEGORIES)


class P3aTemplateFillTest(unittest.TestCase):
    """P3a 模板落库：国家历史/新闻/战略区域/补给区域/初始部队完全版。

    断言模板能被 TemplateScheduler 搜索到且包含真实游戏字段（对照游戏本体格式）。
    """

    def _sched(self):
        from template_scheduler import TemplateScheduler
        return TemplateScheduler(
            templates_dir=os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "..", "templates"))

    def _read_base(self, sched, template_type):
        hits = sched.search_templates(template_type=template_type)
        base = next(h for h in hits if h["name"] == "基础模板")
        with open(base["filepath"], "r", encoding="utf-8-sig") as f:
            return f.read()

    def test_country_history_templates(self):
        """国家历史文件分类（原为空目录）现含基础+项目模板，内容含真实语句。"""
        sched = self._sched()
        hits = sched.search_templates(template_type="country_history")
        names = {h["name"]: h["usage"] for h in hits}
        self.assertIn("基础模板", names)
        self.assertIn("项目模板", names)
        base = self._read_base(sched, "country_history")
        for key in ("set_politics", "set_popularities", "set_technology",
                    "recruit_character", "add_ideas", "set_stability"):
            self.assertIn(key, base)

    def test_news_templates(self):
        """新闻：基础(file)+项目(node)，含 news_event 与图片字段。"""
        sched = self._sched()
        hits = sched.search_templates(template_type="新闻")
        names = {h["name"]: h["usage"] for h in hits}
        self.assertIn("基础模板", names)
        self.assertIn("项目模板", names)
        self.assertEqual(names["基础模板"], "file")
        self.assertEqual(names["项目模板"], "node")
        base = self._read_base(sched, "新闻")
        for key in ("add_namespace", "news_event", "picture", "major = yes"):
            self.assertIn(key, base)

    def test_strategic_region_templates(self):
        """战略区域：strategic_region + provinces + weather。"""
        sched = self._sched()
        base = self._read_base(sched, "战略区域")
        for key in ("strategic_region", "provinces", "weather", "period"):
            self.assertIn(key, base)

    def test_supply_area_templates(self):
        """补给区域：supply_area + states。"""
        sched = self._sched()
        base = self._read_base(sched, "补给区域")
        for key in ("supply_area", "value", "states"):
            self.assertIn(key, base)

    def test_initial_oob_full_template(self):
        """初始部队完全版：含 instant_effect 生产 + 海军舰队 + 空军联队。"""
        sched = self._sched()
        hits = sched.search_templates(template_type="初始部队")
        full = next((h for h in hits if h["name"] == "完整版模板"), None)
        self.assertIsNotNone(full, "初始部队应有完整版模板")
        with open(full["filepath"], "r", encoding="utf-8-sig") as f:
            content = f.read()
        for key in ("division_names_group", "air_wings", "fleet = {",
                    "task_force", "add_equipment_production",
                    "instant_effect", "start_equipment_factor"):
            self.assertIn(key, content)

    def test_dialog_categories_registered(self):
        """模板搜索对话框分类已注册 新闻/战略区域/补给区域。"""
        from template_dialog import CATEGORIES
        for entry in (("新闻", "新闻"), ("战略区域", "战略区域"),
                      ("补给区域", "补给区域")):
            self.assertIn(entry, CATEGORIES)


class UniqueIdScannerTest(unittest.TestCase):
    """唯一标识符扫描器：跨 mod+game 检出重复国策/决议/事件/角色等。"""

    def _mkroots(self):
        mod = _mkdtemp("uid_mod_")
        game = _mkdtemp("uid_game_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        return mod, game

    def _put(self, root, rel, content):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_detects_focus_node_and_tree_conflicts(self):
        """国策节点 ID 与国策树 ID 分开统计，跨文件检出重复。"""
        from unique_id_scanner import scan_duplicates
        mod, game = self._mkroots()
        self._put(mod, "common/national_focus/a.txt",
                  'focus_tree = { id = GER_focus }\n'
                  'focus = { id = GER_DUP }\n')
        self._put(game, "common/national_focus/b.txt",
                  'focus = { id = GER_DUP }\n'
                  'focus_tree = { id = GER_focus }\n')
        dups = scan_duplicates(mod, game, ["focus", "focus_tree", "decision"])
        self.assertIn("GER_DUP", dups.get("focus", {}))
        self.assertIn("GER_focus", dups.get("focus_tree", {}))
        # 节点 ID 与树 ID 不属于同一类型：互不污染
        self.assertNotIn("GER_focus", dups.get("focus", {}))
        self.assertNotIn("GER_DUP", dups.get("focus_tree", {}))

    def test_detects_event_duplicates(self):
        """事件用 命名空间.编号 汇总，跨文件检出重复。"""
        from unique_id_scanner import scan_duplicates
        mod, game = self._mkroots()
        self._put(mod, "events/a.txt", 'add_namespace = my_mod\n'
                  'country_event = { id = my_mod.1 }')
        self._put(game, "events/b.txt", 'country_event = { id = my_mod.1 }')
        dups = scan_duplicates(mod, game, ["event"])
        self.assertIn("my_mod.1", dups.get("event", {}))

    def test_no_duplicates_returns_empty(self):
        """无重复时返回空字典（不误报）。"""
        from unique_id_scanner import scan_duplicates
        mod, game = self._mkroots()
        self._put(mod, "events/a.txt", 'country_event = { id = my_mod.1 }')
        self._put(game, "events/b.txt", 'country_event = { id = my_mod.2 }')
        self.assertNotIn("my_mod.1", scan_duplicates(mod, game, ["event"]))

    def test_cli_returns_one_on_dup(self):
        """CLI 退出码：有重复即 1。"""
        import subprocess
        mod = _mkdtemp("uid_cli_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        self._put(mod, "events/a.txt", 'country_event = { id = cli.1 }')
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script = os.path.join(root, "tools", "unique_id_scanner.py")
        out = subprocess.run(
            [sys.executable, script, "--mod", mod, "--game", mod,
             "--types", "event"],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)


class DesignLayoutSyncTest(unittest.TestCase):
    """设计器布局/锁定槽/空配件提示/同款跨国家同步。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make_env(self):
        from plane_design import _AIRFRAMES_CACHE, _PLANE_MODULES_CACHE, \
            _PLANE_VARIANTS_CACHE
        mod = _mkdtemp("dsh_layout_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        eq = os.path.join(mod, "common", "units", "equipment")
        os.makedirs(os.path.join(eq, "modules"), exist_ok=True)
        with open(os.path.join(eq, "plane_airframes.txt"),
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
                    '\t\t\tlocked_slot = {\n'
                    '\t\t\t\trequired = no\n'
                    '\t\t\t\tallowed_module_categories = { }\n'
                    '\t\t\t}\n'
                    '\t\t}\n'
                    '\t}\n'
                    '\tsmall_plane_airframe_1 = {\n'
                    '\t\tarchetype = small_plane_airframe\n'
                    '\t\tmodule_slots = inherit\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(eq, "modules", "00_plane_modules.txt"),
                  "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tfighter_weapon_1 = {\n'
                    '\t\tabbreviation = "fw1"\n'
                    '\t\tcategory = fighter_weapon\n'
                    '\t\tadd_stats = { air_attack = 2 }\n'
                    '\t}\n'
                    '\tengine_1_1x = {\n'
                    '\t\tabbreviation = "e11"\n'
                    '\t\tcategory = engine\n'
                    '\t\tadd_stats = { thrust = 11 }\n'
                    '\t}\n'
                    '}\n')
        cdir = os.path.join(mod, "history", "countries")
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "AAA.txt"), "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Shared"\n'
                    '\ttype = small_plane_airframe_1\n'
                    '\tmodules = {\n'
                    '\t\tfixed_main_weapon_slot = fighter_weapon_1\n'
                    '\t\tspecial_type_slot_1 = empty\n'
                    '\t}\n'
                    '}\n')
        with open(os.path.join(cdir, "BBB.txt"), "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Shared"\n'
                    '\ttype = small_plane_airframe_1\n'
                    '}\n')
        with open(os.path.join(cdir, "CCC.txt"), "w", encoding="utf-8") as f:
            f.write('create_equipment_variant = {\n'
                    '\tname = "Empty"\n'
                    '\ttype = small_plane_airframe_1\n'
                    '}\n')
        _AIRFRAMES_CACHE.clear()
        _PLANE_MODULES_CACHE.clear()
        _PLANE_VARIANTS_CACHE.clear()
        return mod

    def test_layout_constants_and_locked_slot(self):
        """飞机 5 列 / 舰艇 6 列；allowed 空槽显示锁定🔒。"""
        from plane_design_dialog import PlaneDesignDialog, PLANE_SLOT_COLS
        from ship_design_dialog import SHIP_SLOT_COLS
        self.assertEqual(PLANE_SLOT_COLS, 5)
        self.assertEqual(SHIP_SLOT_COLS, 6)
        mod = self._make_env()
        dlg = PlaneDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.current_name, "Shared")
        self.assertEqual(len(dlg._slot_buttons), 3)
        locked = dlg._slot_buttons["locked_slot"]
        self.assertEqual(locked.text(), "🔒")
        self.assertFalse(locked.isEnabled(), "锁定槽应禁用")
        dlg.close()

    def test_empty_design_shows_hint_and_same_name(self):
        """空配件设计显示默认配置提示；同款标签显示国家数。"""
        from plane_design_dialog import PlaneDesignDialog
        mod = self._make_env()
        dlg = PlaneDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        # Shared 同款 2 国（AAA/BBB）
        self.assertIn("同款 2 国", dlg.same_name_label.text())
        # 切到 CCC 国家，选 Empty（空设计）
        cidx = dlg.country_combo.findData("CCC")
        dlg.country_combo.setCurrentIndex(cidx)
        self.app.processEvents()
        idx = dlg.design_combo.findData("Empty")
        dlg.design_combo.setCurrentIndex(idx)
        self.app.processEvents()
        self.assertIsNotNone(dlg._empty_hint, "空设计应显示默认配置提示")
        self.assertIn("默认配置", dlg._empty_hint.text())
        dlg.close()

    def test_sync_writes_to_other_country(self):
        """同步到所有同款：把当前配置写入其他国家的同名设计。"""
        from unittest.mock import patch
        from PyQt6.QtWidgets import QMessageBox
        from plane_design_dialog import PlaneDesignDialog
        mod = self._make_env()
        dlg = PlaneDesignDialog(mod, "")
        dlg.show()
        self.app.processEvents()
        with patch("plane_design_dialog.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.Yes), \
                patch("plane_design_dialog.QMessageBox.information"):
            dlg._sync_to_all_same_name()
        bbb = os.path.join(mod, "history", "countries", "BBB.txt")
        with open(bbb, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("fixed_main_weapon_slot = fighter_weapon_1", content,
                      "同步应把当前模块写入 BBB 的同名设计")
        dlg.close()


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


class FocusOrderPickerTest(unittest.TestCase):
    """国策顺序点选：依赖删除、插入、顺序操作。"""

    def _data(self):
        return {
            "a": {"draw": {"prerequisite": []}},
            "b": {"draw": {"prerequisite": ["a"]}},
            "c": {"draw": {"prerequisite": ["b"]}},
            "d": {"draw": {"prerequisite": []}},
        }

    def test_dependent_focuses(self):
        from focus_order_picker import dependent_focuses
        deps = dependent_focuses(self._data(), "a")
        self.assertEqual(deps, {"b", "c"})

    def test_insert_after(self):
        from focus_order_picker import insert_after
        self.assertEqual(insert_after(["a", "d"], "a", "b"),
                         ["a", "b", "d"])
        self.assertEqual(insert_after(["a"], "x", "b"), ["a", "b"])

    def test_remove_focus_with_dependents(self):
        from focus_order_picker import remove_focus_with_dependents
        ordered = ["a", "b", "c", "d"]
        self.assertEqual(
            remove_focus_with_dependents(ordered, self._data(), "a"), ["d"])


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


class PdxCompareOperatorTest(unittest.TestCase):
    """比较运算符支持：触发/效果块中的 `key OP value` 语句。

    覆盖 tree_node（树编辑器）与 pdx_parser（字典输出）两条解析路径：
    - 六种运算符（>= <= == != > <）都能被识别；
    - 树解析将语句合并为单节点并 round-trip 保真（不加引号、不加等号）；
    - 字典解析将语句存入块内 'list'（不污染具名键）。
    """

    def setUp(self):
        self.app = None
        try:
            from PyQt6.QtWidgets import QApplication
            self.app = QApplication.instance() or QApplication([])
        except Exception:
            pass

    def _tree_roundtrip(self, block_text):
        from tree_node import tree_from_pdx_text
        src = "available = {\n%s\n}" % "\n".join(block_text)
        root = tree_from_pdx_text(src)
        return root.to_pdx()

    def test_tree_all_operators_roundtrip(self):
        block = [
            "has_political_power > 100",
            "date > 1936.1.1",
            "num_of_controlled_states >= 5",
            "has_war_with != GER",
            "prestige < 50",
            "anything <= 3",
            "exact == 7",
        ]
        out = self._tree_roundtrip(block)
        for stmt in block:
            self.assertIn(stmt, out)
        # 不得加引号或插入等号
        self.assertNotIn('"> 100"', out)
        self.assertNotIn("= >", out)
        self.assertNotIn("= =", out)

    def test_tree_single_statement_node_not_fragmented(self):
        # 语句应合并为单个（空键、raw_lines 保真）节点，而非三个空值节点。
        from tree_node import tree_from_pdx_text
        root = tree_from_pdx_text("available = {\nhas_pp > 10\n}")
        avail = root.children[0]
        stmt_nodes = [c for c in avail.children if c.value == "has_pp > 10"]
        self.assertEqual(len(stmt_nodes), 1)
        self.assertEqual(stmt_nodes[0].key, "")
        # 不存在被拆成多个空值节点的残留
        empty_keys = [c.key for c in avail.children if c.key]
        self.assertNotIn("has_pp", empty_keys)

    def test_dict_parser_comparison_in_list(self):
        from pdx_parser import parse_pdx_script
        d = parse_pdx_script(
            "available = { has_political_power >= 100 exact == 7 tag = GER }")
        self.assertIn("has_political_power >= 100", d["available"]["list"])
        self.assertIn("exact == 7", d["available"]["list"])
        # 具名键不受影响
        self.assertEqual(d["available"]["tag"], "GER")

    def test_dict_parser_operator_order_vs_equals(self):
        # `==` 不能被 `=` 抢先切成两个 token（多字符运算符优先匹配）。
        from pdx_parser import parse_pdx_script
        d = parse_pdx_script("a = { x == 3 }")
        self.assertIn("x == 3", d["a"]["list"])
        self.assertNotIn("x = =", d["a"])

    def test_tree_equals_statement_not_queried(self):
        # `exact == 7` 不能被解析成空值键 `exact` + 额外 token。
        from tree_node import tree_from_pdx_text
        root = tree_from_pdx_text("available = {\nexact == 7\n}")
        avail = root.children[0]
        keys = [c.key for c in avail.children if c.key]
        self.assertNotIn("exact", keys)
        self.assertTrue(any(c.value == "exact == 7" for c in avail.children))


class LocalisationEditorDataTest(unittest.TestCase):
    """本地化编辑器数据层：扫描/合并/upsert/delete/修正筛选。"""

    def setUp(self):
        self.tmp = _mkdtemp("loc_edit_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        self.game = os.path.join(self.tmp, "game")
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        os.makedirs(os.path.join(self.game, "localisation", "simp_chinese"))

    def _write(self, root, filename, content):
        path = os.path.join(root, "localisation", "simp_chinese", filename)
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(content)
        return path

    def test_list_loc_files_finds_yml(self):
        from localisation_editor_data import list_loc_files
        self._write(self.mod, "test_l_simp_chinese.yml", "l_simp_chinese:\n FOO: \"foo\"\n")
        files = list_loc_files(self.mod)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("test_l_simp_chinese.yml"))

    def test_build_entries_merges_mod_and_game(self):
        from localisation_editor_data import build_entries
        self._write(self.game, "game_l_simp_chinese.yml",
                    "l_simp_chinese:\n FOCUS_A: \"Game Name\"\n MODIFIER_X: \"Game Mod\"\n")
        self._write(self.mod, "mod_l_simp_chinese.yml",
                    "l_simp_chinese:\n FOCUS_A: \"Mod Name\"\n")
        entries = build_entries(self.mod, self.game)
        by_key = {e["key"]: e for e in entries}
        self.assertIn("FOCUS_A", by_key)
        self.assertEqual(by_key["FOCUS_A"]["value"], "Mod Name")
        self.assertEqual(by_key["FOCUS_A"]["game_value"], "Game Name")
        self.assertEqual(by_key["FOCUS_A"]["source"], "mod")
        self.assertIn("MODIFIER_X", by_key)
        self.assertEqual(by_key["MODIFIER_X"]["source"], "game")
        self.assertTrue(by_key["MODIFIER_X"]["file"] is None)

    def test_upsert_creates_and_updates_preserving_order(self):
        from localisation_editor_data import upsert_loc_entry
        target = self._write(self.mod, "mod_l_simp_chinese.yml",
                             "l_simp_chinese:\n A: \"a\"\n")
        self.assertTrue(upsert_loc_entry(target, "B", "b"))
        self.assertTrue(upsert_loc_entry(target, "A", "a2"))
        with open(target, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn('A: "a2"', content)
        self.assertIn('B: "b"', content)
        self.assertLess(content.index("A"), content.index("B"))

    def test_delete_removes_only_target_key(self):
        from localisation_editor_data import delete_loc_entry
        target = self._write(self.mod, "mod_l_simp_chinese.yml",
                             "l_simp_chinese:\n A: \"a\"\n B: \"b\"\n")
        self.assertTrue(delete_loc_entry(target, "A"))
        with open(target, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertNotIn('A: "a"', content)
        self.assertIn('B: "b"', content)

    def test_is_modifier_key(self):
        from localisation_editor_data import is_modifier_key
        self.assertTrue(is_modifier_key("MODIFIER_POPULARITY_SCORE"))
        self.assertTrue(is_modifier_key("opinion_relation"))
        self.assertTrue(is_modifier_key("dynamic_modifier_ab"))
        self.assertFalse(is_modifier_key("focus_war_plan"))


class LocalisationEditorDialogSmokeTest(unittest.TestCase):
    """本地化编辑器对话框 offscreen 冒烟：构建、筛选、新增。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = _mkdtemp("loc_dlg_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        path = os.path.join(self.mod, "localisation", "simp_chinese",
                            "mod_l_simp_chinese.yml")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("l_simp_chinese:\n FOCUS_A: \"国策A\"\n MODIFIER_X: \"修正X\"\n")

    def test_dialog_construct_and_filter_modifier(self):
        from localisation_editor_dialog import LocalisationEditorDialog
        dlg = LocalisationEditorDialog(mod_path=self.mod, hoi4_path="", parent=None)
        self.app.processEvents()
        self.assertGreaterEqual(dlg.table.rowCount(), 2)
        dlg.modifier_check.setChecked(True)
        self.app.processEvents()
        self.assertEqual(dlg.table.rowCount(), 1)
        key_item = dlg.table.item(0, 0)
        self.assertEqual(key_item.text(), "MODIFIER_X")

    def test_dialog_add_entry_creates_file(self):
        from localisation_editor_dialog import LocalisationEditorDialog
        from localisation_editor_data import upsert_loc_entry
        dlg = LocalisationEditorDialog(mod_path=self.mod, hoi4_path="", parent=None)
        self.app.processEvents()
        target = os.path.join(self.mod, "localisation", "simp_chinese",
                              "mod_l_simp_chinese.yml")
        self.assertTrue(dlg._target_filepath())
        ok = upsert_loc_entry(target, "NEW_KEY", "新值")
        self.assertTrue(ok)
        with open(target, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("NEW_KEY", content)


class LocalisationEditorLanguageTest(unittest.TestCase):
    """本地化编辑器多语言：默认中文、英文可选、批量补写。"""

    def setUp(self):
        self.tmp = _mkdtemp("loc_lang_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        self.game = os.path.join(self.tmp, "game")
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        os.makedirs(os.path.join(self.mod, "localisation", "english"))
        os.makedirs(os.path.join(self.game, "localisation", "simp_chinese"))
        os.makedirs(os.path.join(self.game, "localisation", "english"))

    def _write_loc(self, root, lang, filename, content):
        path = os.path.join(root, "localisation", lang, filename)
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(content)
        return path

    def test_effective_dict_default_chinese(self):
        from localisation_editor_data import load_effective_dict
        self._write_loc(self.game, "simp_chinese", "game_l_simp_chinese.yml",
                        "l_simp_chinese:\n FOO: \"游戏中文\"\n")
        self._write_loc(self.mod, "simp_chinese", "mod_l_simp_chinese.yml",
                        "l_simp_chinese:\n FOO: \"mod中文\"\n BAR: \"酒吧\"\n")
        d = load_effective_dict(self.mod, self.game, "simp_chinese")
        self.assertEqual(d["FOO"], "mod中文")
        self.assertEqual(d["BAR"], "酒吧")

    def test_build_entries_english_with_chinese_reference(self):
        from localisation_editor_data import build_entries, load_effective_dict
        self._write_loc(self.mod, "english", "mod_l_english.yml",
                        "l_english:\n FOO: \"Mod English\"\n")
        self._write_loc(self.mod, "simp_chinese", "mod_l_simp_chinese.yml",
                        "l_simp_chinese:\n FOO: \"Mod 中文\"\n")
        self._write_loc(self.game, "english", "game_l_english.yml",
                        "l_english:\n BAR: \"Game English\"\n")
        entries = build_entries(self.mod, self.game, "english")
        by_key = {e["key"]: e for e in entries}
        self.assertEqual(by_key["FOO"]["value"], "Mod English")
        self.assertEqual(by_key["FOO"]["source"], "mod")
        self.assertEqual(by_key["BAR"]["value"], "Game English")
        self.assertEqual(by_key["BAR"]["source"], "game")
        chinese = load_effective_dict(self.mod, self.game, "simp_chinese")
        self.assertEqual(chinese["FOO"], "Mod 中文")

    def test_batch_fill_missing_chinese(self):
        from localisation_editor_data import batch_fill_missing_loc
        # 创建含实体 key 的修正定义文件
        mod_dir = os.path.join(self.mod, "common", "opinion_modifiers")
        os.makedirs(mod_dir, exist_ok=True)
        with open(os.path.join(mod_dir, "mod.txt"), "w", encoding="utf-8") as f:
            f.write("opinion_modifiers = {\n\tTEST_MOD = { value = 10 }\n}\n")
        written, target = batch_fill_missing_loc(self.mod, self.game, "simp_chinese")
        self.assertGreaterEqual(written, 1)
        self.assertTrue(os.path.isfile(target))
        with open(target, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("TEST_MOD", content)

    def test_upsert_english_file(self):
        from localisation_editor_data import upsert_loc_entry
        target = self._write_loc(self.mod, "english", "mod_l_english.yml",
                                 "l_english:\n A: \"a\"\n")
        self.assertTrue(upsert_loc_entry(target, "B", "bee", "english"))
        with open(target, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn('B: "bee"', content)
        self.assertIn('l_english:', content)


class LocalisationCategoryTest(unittest.TestCase):
    """本地化词条分类筛选。"""

    def test_categorise_key(self):
        from localisation_editor_data import categorise_key
        self.assertEqual(categorise_key("focus_war_plan"), "国策")
        self.assertEqual(categorise_key("decision_test"), "决议")
        self.assertEqual(categorise_key("event_test.title"), "事件")
        self.assertEqual(categorise_key("idea_xxx"), "理念")
        self.assertEqual(categorise_key("tech_infantry"), "科技")
        self.assertEqual(categorise_key("MODIFIER_AAA"), "修正")
        self.assertEqual(categorise_key("opinion_bbb"), "修正")
        self.assertEqual(categorise_key("GER_leader_hitler"), "人物")
        self.assertEqual(categorise_key("TOOLTIP_TRAIN"), "界面/辅助")
        self.assertEqual(categorise_key("random_key"), "其他")

    def test_dialog_category_filter(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        tmp = _mkdtemp("loc_cat_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        mod = os.path.join(tmp, "mod")
        os.makedirs(os.path.join(mod, "localisation", "simp_chinese"))
        path = os.path.join(mod, "localisation", "simp_chinese", "mod_l_simp_chinese.yml")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("l_simp_chinese:\n focus_aa: \"国策\"\n modifier_bb: \"修正\"\n")
        from localisation_editor_dialog import LocalisationEditorDialog
        dlg = LocalisationEditorDialog(mod_path=mod, hoi4_path="", parent=None)
        app.processEvents()
        self.assertGreaterEqual(dlg.table.rowCount(), 2)
        idx = dlg.category_combo.findData("国策")
        dlg.category_combo.setCurrentIndex(idx)
        app.processEvents()
        self.assertEqual(dlg.table.rowCount(), 1)
        self.assertEqual(dlg.table.item(0, 0).text(), "focus_aa")


class QuickLocalisationEditSmokeTest(unittest.TestCase):
    """快速本地化编辑小窗口 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = _mkdtemp("quick_loc_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        path = os.path.join(self.mod, "localisation", "simp_chinese", "mod_l_simp_chinese.yml")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("l_simp_chinese:\n FOO: \"旧值\"\n")
        self.path = path

    def test_quick_dialog_prefills_existing_value(self):
        from quick_localisation_edit import QuickLocalisationEditDialog
        dlg = QuickLocalisationEditDialog(
            key="FOO", mod_path=self.mod, hoi4_path="", parent=None)
        self.app.processEvents()
        self.assertEqual(dlg.value_edit.text(), "旧值")
        self.assertEqual(dlg._target_filepath(), self.path)

    def test_quick_dialog_switch_language_uses_english_dir(self):
        from quick_localisation_edit import QuickLocalisationEditDialog
        os.makedirs(os.path.join(self.mod, "localisation", "english"), exist_ok=True)
        en_path = os.path.join(self.mod, "localisation", "english", "mod_l_english.yml")
        with open(en_path, "w", encoding="utf-8-sig") as f:
            f.write("l_english:\n FOO: \"Old English\"\n")
        dlg = QuickLocalisationEditDialog(
            key="FOO", mod_path=self.mod, hoi4_path="", parent=None)
        self.app.processEvents()
        self.assertEqual(dlg.value_edit.text(), "旧值")
        idx = dlg.lang_combo.findData("english")
        dlg.lang_combo.setCurrentIndex(idx)
        self.app.processEvents()
        self.assertEqual(dlg.value_edit.text(), "Old English")
        self.assertEqual(dlg._target_filepath(), en_path)


class QuickLocalisationDescTest(unittest.TestCase):
    """快速本地化编辑：BOP 名称+描述。"""

    def setUp(self):
        self.tmp = _mkdtemp("quick_loc_desc_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        path = os.path.join(self.mod, "localisation", "simp_chinese", "mod_l_simp_chinese.yml")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("l_simp_chinese:\n FOO: \"名称\"\n FOO_desc: \"旧描述\"\n")
        self.path = path

    def test_desc_dialog_prefills_both_fields(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication.instance() or QApplication([])
        from quick_localisation_edit import QuickLocalisationEditDialog
        dlg = QuickLocalisationEditDialog(
            key="FOO", mod_path=self.mod, hoi4_path="",
            desc_key="FOO_desc", parent=None)
        app.processEvents()
        self.assertEqual(dlg.value_edit.text(), "名称")
        self.assertIsNotNone(dlg.desc_edit)
        self.assertEqual(dlg.desc_edit.text(), "旧描述")
        result = dlg.get_result()
        self.assertEqual(result["desc_key"], "FOO_desc")
        self.assertEqual(result["desc_value"], "旧描述")


class QuickLocMenuHelperTest(unittest.TestCase):
    """快速本地化右键菜单安装辅助。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_install_context_menu_sets_policy(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QLabel
        from quick_loc_menu import install_context_menu
        label = QLabel("test")
        install_context_menu(label, mod_path="/tmp/mod", hoi4_path="",
                             key_provider=lambda: "FOO")
        self.assertEqual(label.contextMenuPolicy(),
                         Qt.ContextMenuPolicy.CustomContextMenu)

    def test_install_combo_context_menu_default_key(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QComboBox
        from quick_loc_menu import install_combo_context_menu
        combo = QComboBox()
        combo.addItem("显示", "BAR")
        install_combo_context_menu(combo, mod_path="/tmp/mod", hoi4_path="")
        self.assertEqual(combo.contextMenuPolicy(),
                         Qt.ContextMenuPolicy.CustomContextMenu)


class QiqiTermImportTest(unittest.TestCase):
    """QIUQI 词条导入解析与合并。"""

    def test_parse_tech_list_keeps_empty_and_section(self):
        from qiqi_term_import import parse_tech_list
        terms = parse_tech_list(
            "1.步兵科技\n\tinfantry_weapons = 1918步枪\n\tinfantry_at2 = \n")
        by_key = {t["key"]: t for t in terms}
        self.assertEqual(by_key["infantry_weapons"]["cn"], "1918步枪")
        self.assertEqual(by_key["infantry_at2"]["cn"], "")
        self.assertIn("原表未填中文", by_key["infantry_at2"]["description"])
        self.assertIn("1.步兵科技", by_key["infantry_weapons"]["tags"])

    def test_parse_traits_pairs_comment_and_value(self):
        from qiqi_term_import import parse_traits
        terms = parse_traits(
            "#领袖\n    #政治类\n        #意识形态\n"
            "            #communism_drift = 0.25\n"
            "            #共产主义理念每日新增支持率: +0.25（原版最高0.1）\n")
        by_key = {t["key"]: t for t in terms}
        t = by_key["communism_drift"]
        self.assertIn("共产主义理念", t["cn"])
        self.assertIn("0.25", t["description"])
        self.assertIn("意识形态", t["tags"])

    def test_parse_navy_and_spirit_and_cabinet(self):
        from qiqi_term_import import parse_navy, parse_national_spirit, parse_cabinet
        navy = parse_navy("####船体####\n固定主炮 fixed_ship_battery_slot\n")
        self.assertEqual(navy[0]["key"], "fixed_ship_battery_slot")
        self.assertEqual(navy[0]["cn"], "固定主炮")
        self.assertIn("船体", navy[0]["tags"])
        spirit = parse_national_spirit("#陆军\noffence #攻击\n")
        self.assertEqual(spirit[0]["key"], "offence")
        self.assertEqual(spirit[0]["cn"], "攻击")
        cab = parse_cabinet("backroom_backstabber 密谋的暗害者 政治点+5% 意识形态抵制+15%\n")
        self.assertEqual(cab[0]["key"], "backroom_backstabber")
        self.assertIn("政治点+5%", cab[0]["description"])

    def test_parse_commands_gbk_decode(self):
        from qiqi_term_import import parse_commands
        raw = "political_power_gain = 1\t#每日获得的政治点数\n".encode("gbk")
        terms = parse_commands(raw.decode("gbk"))
        self.assertEqual(terms[0]["cn"], "每日获得的政治点数")

    def test_build_terms_qiuqi_conflict_last_wins(self):
        from qiqi_term_import import build_terms_from_texts
        terms = build_terms_from_texts({
            "原版科技种类.txt": "light_air = 分类名\ninfantry_weapons = 旧名\n",
            "科技列表（截至抗战DLC）.txt": "1.步兵科技\n\tinfantry_weapons = 1918步枪\n",
        })
        by_key = {t["key"]: t for t in terms}
        self.assertEqual(by_key["infantry_weapons"]["cn"], "1918步枪")
        self.assertEqual(by_key["light_air"]["cn"], "分类名")

    def test_write_qiqi_terms_output(self):
        import json
        from qiqi_term_import import write_qiqi_terms
        tmp = _mkdtemp("qiqi_import_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        src = os.path.join(tmp, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "装备类型汇总.txt"), "w", encoding="utf-8") as f:
            f.write("anti_air_equipment = 牵引式防空炮\n")
        out = os.path.join(tmp, "out.json")
        n = write_qiqi_terms(out, src)
        self.assertGreaterEqual(n, 1)
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["terms"][0]["key"], "anti_air_equipment")


class TermRegistryQiqiWinsTest(unittest.TestCase):
    """词条注册表：QIUQI 文件在后 → 同键冲突 QIUQI 胜出且不重复。"""

    def setUp(self):
        self.tmp = _mkdtemp("term_reg_qiqi_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, name, terms):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            import json
            json.dump({"terms": terms}, f, ensure_ascii=False)
        return path

    def test_qiqi_last_wins_and_no_duplicate(self):
        from term_registry import TermRegistry
        f1 = self._write("effect_terms.json", [
            {"key": "infantry_weapons", "cn": "旧译", "tags": ["装备"]}])
        f2 = self._write("qiqi_terms.json", [
            {"key": "infantry_weapons", "cn": "1918步枪", "tags": ["科技"]}])
        reg = TermRegistry(term_files=[f1, f2])
        reg.load()
        self.assertEqual(reg.get_cn("infantry_weapons"), "1918步枪")
        res = reg.search("infantry_weapons")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["cn"], "1918步枪")


class QiqiGroupImportTest(unittest.TestCase):
    """QIUQI 分文件导入：mod常用代码 / 外交 / TFR / TNO。"""

    def test_parse_collection_hash_and_trailing_cn(self):
        from qiqi_term_import import parse_collection
        text = (
            "#外交\n"
            "is_major = yes 是主要国家\n"
            "income_growth_factor = -0.05 #月度收入增长\n"
            "set_temp_variable = { var = x } #设定临时变量\n"
            "has_war_with = TAG 与某国战争中\n"
        )
        terms = parse_collection(text, tags=["常用代码"])
        by_key = {t["key"]: t for t in terms}
        self.assertEqual(by_key["is_major"]["cn"], "是主要国家")
        self.assertEqual(by_key["income_growth_factor"]["cn"], "月度收入增长")
        self.assertEqual(by_key["set_temp_variable"]["cn"], "设定临时变量")
        self.assertIn("外交", by_key["is_major"]["tags"])
        self.assertIn("常用代码", by_key["is_major"]["tags"])

    def test_import_all_writes_separate_files(self):
        import json
        from qiqi_term_import import import_all
        tmp = _mkdtemp("qiqi_group_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        src = os.path.join(tmp, "qsrc")
        code_dir = os.path.join(src, "资料", "基础代码", "代码提词")
        os.makedirs(code_dir, exist_ok=True)
        with open(os.path.join(code_dir, "mod常用代码（dream修订）.txt"),
                  "w", encoding="utf-8") as f:
            f.write("has_war_with = TAG 与某国战争中\n")
        out = os.path.join(tmp, "out")
        results = import_all(out, src)
        names = [n for n, _c in results]
        self.assertIn("qiqi_terms.json", names)
        self.assertIn("qiqi_modcode_terms.json", names)
        self.assertIn("qiqi_diplo_terms.json", names)
        self.assertIn("qiqi_tfr_terms.json", names)
        self.assertIn("qiqi_tno_terms.json", names)
        with open(os.path.join(out, "qiqi_modcode_terms.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        keys = [t["key"] for t in data["terms"]]
        self.assertIn("has_war_with", keys)

    def test_term_registry_loads_all_qiqi_files(self):
        from term_registry import TERM_FILES
        names = [os.path.basename(p) for p in TERM_FILES]
        for expected in ("qiqi_terms.json", "qiqi_modcode_terms.json",
                         "qiqi_diplo_terms.json", "qiqi_tfr_terms.json",
                         "qiqi_tno_terms.json"):
            self.assertIn(expected, names)


class EntityResourceDataTest(unittest.TestCase):
    """实体配套资源数据层测试。"""

    def setUp(self):
        self.tmp = _mkdtemp("entity_res_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "national_focus"))
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        os.makedirs(os.path.join(self.mod, "gfx", "interface", "goals"))
        os.makedirs(os.path.join(self.mod, "interface"), exist_ok=True)

        with open(os.path.join(self.mod, "common", "national_focus", "ger.txt"),
                  "w", encoding="utf-8") as f:
            f.write(
                "focus_tree = {\n"
                " id = GER_proj\n"
                " country = { factor = 0 }\n"
                " focus = { id = GER_focus1 icon = GFX_test_icon }\n"
                "}\n")

        # 注册普通 GFX（无光效）
        with open(os.path.join(self.mod, "interface", "goals_mod.gfx"),
                  "w", encoding="utf-8") as f:
            f.write('spriteTypes = {\n'
                    '\tspriteType = {\n'
                    '\t\tname = "GFX_test_icon"\n'
                    '\t\ttexturefile = "gfx/interface/goals/GFX_test_icon.png"\n'
                    '\t}\n'
                    '}\n')
        # 贴图文件存在
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_test_icon.png"), "w").close()

        with open(os.path.join(self.mod, "localisation", "simp_chinese", "ger_l_simp_chinese.yml"),
                  "w", encoding="utf-8-sig") as f:
            f.write("l_simp_chinese:\n GER_focus1: \"已有名\"\n")

    def test_collect_resource_item(self):
        from entity_resource_data import collect_resource_items
        items = collect_resource_items(
            self.mod, "", filepath="common/national_focus/ger.txt")
        self.assertTrue(items)
        item = items[0]
        self.assertEqual(item["key"], "GER_focus1")
        self.assertEqual(item["icon"], "GFX_test_icon")
        self.assertTrue(item["icon_registered"])
        self.assertTrue(item["icon_file_exists"])
        self.assertFalse(item["shine_registered"])

    def test_ensure_shine_writes_once(self):
        from entity_resource_data import ensure_shine_gfx
        ok = ensure_shine_gfx(self.mod, "GFX_test_icon", "gfx/interface/goals/GFX_test_icon.png")
        self.assertTrue(ok)
        shine_path = os.path.join(self.mod, "interface", "goals_shine_mod.gfx")
        self.assertTrue(os.path.isfile(shine_path))
        content = open(shine_path, "r", encoding="utf-8").read()
        self.assertIn("GFX_test_icon_shine", content)
        # 二次调用：已有，返回 False 不修改
        self.assertFalse(ensure_shine_gfx(self.mod, "GFX_test_icon", "gfx/interface/goals/GFX_test_icon.png"))

    def test_save_loc_edits_writes_mod(self):
        from entity_resource_data import save_loc_edits
        written = save_loc_edits(self.mod, [
            {"key": "GER_focus1_desc", "value": "新描述", "lang": "simp_chinese"},
        ])
        self.assertEqual(written, 1)
        target = os.path.join(self.mod, "localisation", "simp_chinese", "generic_mod_l_simp_chinese.yml")
        self.assertTrue(os.path.isfile(target))
        content = open(target, "r", encoding="utf-8-sig").read()
        self.assertIn('GER_focus1_desc: "新描述"', content)


class EntityResourceDialogSmokeTest(unittest.TestCase):
    """实体配套资源工作台 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = _mkdtemp("entity_res_dlg_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "national_focus"))
        os.makedirs(os.path.join(self.mod, "gfx", "interface", "goals"))
        with open(os.path.join(self.mod, "common", "national_focus", "x.txt"),
                  "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n id = ABC_pj\n country = { factor = 0 }\n"
                    " focus = { id = ABC_f1 icon = GFX_abc }\n}\n")
        self.gfx = os.path.join(self.mod, "interface", "goals_mod.gfx")
        os.makedirs(os.path.dirname(self.gfx), exist_ok=True)
        with open(self.gfx, "w", encoding="utf-8") as f:
            f.write('spriteTypes = {\n spriteType = {\n name = "GFX_abc"\n'
                    ' texturefile = "gfx/interface/goals/GFX_abc.png"\n}\n}\n')
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_abc.png"), "w").close()

    def test_dialog_builds_and_fill_shine(self):
        from entity_resource_dialog import EntityResourceDialog
        dlg = EntityResourceDialog(
            mod_path=self.mod, hoi4_path="",
            initial_file="common/national_focus/x.txt")
        self.app.processEvents()
        self.assertGreaterEqual(dlg.table.rowCount(), 1)
        # 自动勾选补光效（mock 掉模态提示框，避免阻塞）
        from unittest import mock
        with mock.patch("entity_resource_dialog.QMessageBox.information"), \
             mock.patch("entity_resource_dialog.QMessageBox.warning"):
            dlg.auto_shine_check.setChecked(True)
            dlg._on_fill_shine()
        self.app.processEvents()
        shine = os.path.join(self.mod, "interface", "goals_shine_mod.gfx")
        self.assertTrue(os.path.isfile(shine))


class PdxFormatTest(unittest.TestCase):
    """PDX 格式化。"""

    def test_format_indents_by_braces(self):
        from pdx_format import format_text
        text = "focus_tree = {\nid = A\nfocus = {\nid = B\n}\n}\n"
        out = format_text(text)
        lines = out.splitlines()
        self.assertEqual(lines[0], "focus_tree = {")
        self.assertEqual(lines[1], "\tid = A")
        self.assertEqual(lines[2], "\tfocus = {")
        self.assertEqual(lines[3], "\t\tid = B")
        self.assertEqual(lines[4], "\t}")

    def test_format_ignores_braces_in_strings(self):
        from pdx_format import format_text
        text = 'x = {\n  name = "a { b } c"\n}\n'
        out = format_text(text)
        # 字符串内的花括号不应影响缩进计数
        self.assertIn('\tname = "a { b } c"', out)
        self.assertEqual(out.splitlines()[-1], "}")

    def test_format_file_writes(self):
        import os
        from pdx_format import format_file
        tmp = _mkdtemp("pdx_fmt_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        p = os.path.join(tmp, "a.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x = {\ny = 1\n}\n")
        self.assertTrue(format_file(p))
        with open(p, "r", encoding="utf-8") as f:
            out = f.read()
        self.assertIn("\ty = 1", out)


class IconBatchTest(unittest.TestCase):
    """图标 GFX 批量注册。"""

    def setUp(self):
        self.tmp = _mkdtemp("icon_batch_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "national_focus"))
        os.makedirs(os.path.join(self.mod, "gfx", "interface", "goals"))
        os.makedirs(os.path.join(self.mod, "interface"))

    def _write_focus(self, icon_field):
        body = ("focus_tree = {\n id = TG_pj\n country = { factor = 0 }\n"
                " focus = { id = TG_a ICONFIELD\n}\n")
        body = body.replace("ICONFIELD", "icon = " + icon_field)
        with open(os.path.join(self.mod, "common", "national_focus", "f.txt"),
                  "w", encoding="utf-8") as f:
            f.write(body)

    def test_register_missing_registers_and_skips(self):
        from icon_batch import register_missing_gfx
        # 有贴图的图标应注册
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_goal_in.svg"), "w").close()
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_goal_have.dds"), "w").close()
        self._write_focus("GFX_goal_have")
        r = register_missing_gfx(self.mod, "common/national_focus/f.txt", "focus")
        self.assertEqual(r["registered"], 1)
        gfx = os.path.join(self.mod, "interface", "goals_mod.gfx")
        self.assertTrue(os.path.isfile(gfx))
        content = open(gfx, "r", encoding="utf-8").read()
        self.assertIn('name = "GFX_goal_have"', content)
        # 再次调用：已是已注册 → 不再写
        r2 = register_missing_gfx(self.mod, "common/national_focus/f.txt", "focus")
        self.assertEqual(r2["registered"], 0)

    def test_skip_when_no_texture(self):
        from icon_batch import register_missing_gfx
        self._write_focus("GFX_goal_missing")
        r = register_missing_gfx(self.mod, "common/national_focus/f.txt", "focus")
        self.assertEqual(r["registered"], 0)
        self.assertEqual(r["skipped_no_texture"], 1)


class EventGeneratorTest(unittest.TestCase):
    """事件生成器。"""

    def test_generate_event(self):
        from event_gen import generate_event
        r = generate_event("my_event", namespace="MYNS")
        self.assertIn("add_namespace = MYNS", r["text"])
        self.assertIn("country_event = {", r["text"])
        self.assertIn("id = MYNS.my_event", r["text"])
        self.assertIn("title = MYNS.my_event.t", r["text"])
        self.assertEqual(len(r["loc"]), 4)
        keys = {x["key"] for x in r["loc"]}
        self.assertIn("MYNS.my_event.t", keys)


class DdsConvertTest(unittest.TestCase):
    """批量 DDS 转换。"""

    def setUp(self):
        self.tmp = _mkdtemp("dds_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_dds_to_png_roundtrip(self):
        from PIL import Image
        from dds_convert import dds_to_png, convert_dir
        src_dir = os.path.join(self.tmp, "in")
        os.makedirs(src_dir)
        dds = os.path.join(src_dir, "a.dds")
        Image.new("RGBA", (4, 4), (0, 128, 255, 255)).save(dds, "DDS")
        img = dds_to_png(dds)
        self.assertTrue(img and os.path.isfile(img))
        self.assertTrue(img.endswith(".png"))
        out = convert_dir(src_dir)
        self.assertEqual(out["count"], 1)
        self.assertTrue(os.path.isfile(os.path.join(src_dir, "a.png")))


class VpLocTest(unittest.TestCase):
    """胜利点本地化生成。"""

    def setUp(self):
        self.tmp = _mkdtemp("vp_loc_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "history", "states"))
        with open(os.path.join(self.mod, "history", "states", "01.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state = {\n\tid = 1\n\tvictory_points = { 10 2 11 1 }\n}\n")
        with open(os.path.join(self.mod, "history", "states", "02.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state = {\n\tid = 2\n\tvictory_points = { 20 5 }\n}\n")

    def test_collect_and_build(self):
        from vp_loc import collect_vps, build_vp_loc_text
        vps = collect_vps(self.mod)
        self.assertEqual(len(vps), 3)
        text = build_vp_loc_text(vps, lang="simp_chinese")
        self.assertIn("l_simp_chinese:", text)
        self.assertIn("VICTORY_POINTS_10", text)
        self.assertIn("VICTORY_POINTS_11", text)
        self.assertIn("VICTORY_POINTS_20", text)


class PdxSorterTest(unittest.TestCase):
    """state/province 排序。"""

    def test_sort_state_file_by_id(self):
        from pdx_sorter import sort_state_file
        text = ("state = { id = 3 owner = ENG }\n"
                "state = { id = 1 owner = FRA }\n"
                "state = { id = 2 owner = GER }\n")
        out = sort_state_file(text)
        self.assertLess(out.index("id = 1"), out.index("id = 2"))
        self.assertLess(out.index("id = 2"), out.index("id = 3"))


class InterfaceRegTest(unittest.TestCase):
    """interface / gfx 批量注册。"""

    def test_register_sprites_missing_only(self):
        from interface_reg import register_sprites
        tmp = _mkdtemp("iface_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        gfx = os.path.join(tmp, "m.gfx")
        with open(gfx, "w", encoding="utf-8") as f:
            f.write('spriteTypes = {\n spriteType = { name = "A" texturefile = "a.png" }\n}\n')
        n = register_sprites(gfx, {"A": "a.png", "B": "b.png"})
        self.assertEqual(n, 1)  # A 已有 → 只注册 B
        content = open(gfx, "r", encoding="utf-8").read()
        self.assertIn('name = "B"', content)


class ErrorLogTest(unittest.TestCase):
    """错误日志分析。"""

    def test_analyze_categories(self):
        from error_log import analyze, summarize
        text = ("[18:00] loc key not found: FOO\n"
                "Could not find coloring for character 'M'\n"
                "unexpected }\n")
        res = analyze(text)
        self.assertTrue(any(r["category"] == "缺本地化键" for r in res))
        self.assertTrue(any(r["category"] == "着色字符错误" for r in res))
        self.assertTrue(any(r["category"] == "括号/引用不匹配" for r in res))
        self.assertEqual(len(res), 3)
        s = summarize(res)
        self.assertEqual(sum(s.values()), 3)


class StateBatchTest(unittest.TestCase):
    """州批量写。"""

    def setUp(self):
        self.tmp = _mkdtemp("state_batch_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "history", "states"))
        self.file = os.path.join(self.mod, "history", "states", "01.txt")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write("state = {\n\tid = 1\n\towner = ENG\n}\n"
                    "state = {\n\tid = 2\n\towner = FRA\n}\n")

    def test_set_manpower_batch(self):
        from state_batch import batch_write
        r = batch_write(self.mod, manpower={"1": 123, "2": 456})
        self.assertEqual(r["manpower"], 2)
        content = open(self.file, "r", encoding="utf-8").read()
        self.assertIn("manpower = 123", content)
        self.assertIn("manpower = 456", content)


class SecondBatchGeneratorTest(unittest.TestCase):
    """第二批内容生成器。"""

    def test_idea_gen(self):
        from idea_gen import generate_ideas
        r = generate_ideas([{"id": "MY_IDEA", "picture": "GFX_p", "modifier": "stability = 0.1"}])
        self.assertIn("MY_IDEA = {", r["text"])
        self.assertIn("picture = GFX_p", r["text"])
        self.assertIn("stability = 0.1", r["text"])
        keys = {x["key"] for x in r["loc"]}
        self.assertIn("MY_IDEA", keys)
        self.assertIn("MY_IDEA_desc", keys)

    def test_ideology_gen(self):
        from ideology_gen import generate_ideologies
        r = generate_ideologies([{"id": "MY_IDEOLOGY"}])
        self.assertIn("MY_IDEOLOGY = {", r["text"])
        self.assertIn("color = {", r["text"])

    def test_character_gen(self):
        from character_gen import generate_characters
        r = generate_characters([{"tag": "AAA", "characters": [{"id": "gen1"}]}])
        self.assertIn("AAA = {", r["text"])
        self.assertIn("gen1 = {", r["text"])

    def test_general_gen(self):
        from general_gen import generate_leader_blocks
        r = generate_leader_blocks([{"name_loc": "AAA_gen1", "ideology": "democratic"}])
        self.assertIn("leader = {", r["text"])
        self.assertIn("ideology = democratic", r["text"])

    def test_country_boot(self):
        from country_boot import generate_country_bootstrap, country_tag_line
        r = generate_country_bootstrap([{"tag": "AAA", "name": "Testland"}])
        self.assertTrue(r["histories"])
        text = next(iter(r["histories"].values()))
        self.assertIn("AAA = {", text)
        self.assertIn('AAA:0 "countries/Testland.txt"', r["tag_lines"])
        self.assertEqual(r["loc"][0]["value"], "Testland")
        self.assertEqual(country_tag_line("BBB", "Bland"), 'BBB:0 "countries/Bland.txt"')

    def test_focus_package_gen(self):
        from focus_package_gen import generate_package, generate_icon_gfx
        focuses = [{"id": "AAA_f1", "icon": "GFX_goal_aaa"}]
        pkg = generate_package(focuses, tree_id="AAA_proj")
        self.assertIn("AAA_f1", pkg["tree"]["text"])
        self.assertIn("focus_tree = {", pkg["tree"]["text"])
        keys = {x["key"] for x in pkg["loc"]}
        self.assertIn("AAA_f1_desc", keys)
        gfx = generate_icon_gfx(focuses)
        self.assertIn('name = "GFX_goal_aaa"', gfx)


class ContentGeneratorDialogSmokeTest(unittest.TestCase):
    """内容生成器工作台 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_generate_ideas_writes_file(self):
        from content_generator_dialog import ContentGeneratorDialog
        from unittest import mock
        tmp = _mkdtemp("gen_dlg_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        dlg = ContentGeneratorDialog(mod_path=tmp)
        self.app.processEvents()
        idx = dlg.type_combo.findData("ideas")
        dlg.type_combo.setCurrentIndex(idx)
        dlg.id_edit.setText("TST_IDEA")
        out = os.path.join(tmp, "ideas.txt")
        dlg.out_edit.setText(out)
        with mock.patch("content_generator_dialog.QMessageBox.information"):
            dlg._on_generate()
        self.assertTrue(os.path.isfile(out))
        content = open(out, "r", encoding="utf-8").read()
        self.assertIn("TST_IDEA = {", content)

    def test_generate_focus_writes_file(self):
        from content_generator_dialog import ContentGeneratorDialog
        from unittest import mock
        tmp = _mkdtemp("gen_dlg_f_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        dlg = ContentGeneratorDialog(mod_path=tmp)
        idx = dlg.type_combo.findData("focus")
        dlg.type_combo.setCurrentIndex(idx)
        dlg.id_edit.setText("AAA_f1,AAA_f2")
        dlg.extra2_edit.setText("AAA_pj")
        out = os.path.join(tmp, "focus.txt")
        dlg.out_edit.setText(out)
        with mock.patch("content_generator_dialog.QMessageBox.information"):
            dlg._on_generate()
        content = open(out, "r", encoding="utf-8").read()
        self.assertIn("AAA_f1", content)


class CharacterDataTest(unittest.TestCase):
    """角色数据层。"""

    def setUp(self):
        self.tmp = _mkdtemp("char_data_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "characters"))
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        self.file = os.path.join(self.mod, "common", "characters", "AAA.txt")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write("characters = {\n"
                    "\tAAA_gen = {\n"
                    "\t\tname = \"AAA_gen\"\n"
                    "\t\tportraits = {\n"
                    "\t\t\tcivilian = {\n"
                    "\t\t\t\tlarge = GFX_P\n"
                    "\t\t\t}\n"
                    "\t\t}\n"
                    "\t\tcountry_leader = {\n"
                    "\t\t\tideology = democratic\n"
                    "\t\t}\n"
                    "\t}\n"
                    "}\n")

    def test_parse_and_render_preserves_roles(self):
        from character_data import load_file, render_character_block
        header, metas, tail = load_file(self.file)
        self.assertEqual(len(metas), 1)
        self.assertEqual(metas[0]["id"], "AAA_gen")
        self.assertEqual(metas[0]["name_loc"], "AAA_gen")
        self.assertIn("civilian", metas[0]["portraits_inner"])
        self.assertEqual(len(metas[0]["roles"]), 1)
        out = render_character_block(metas[0])
        self.assertIn("country_leader", out)  # roles 保留
        self.assertIn("name = \"AAA_gen\"", out)

    def test_save_roundtrip(self):
        from character_data import load_file, save_file
        header, metas, tail = load_file(self.file)
        metas[0]["name_loc"] = "AAA_gen_new"
        save_file(self.file, header, metas, tail)
        content = open(self.file, "r", encoding="utf-8").read()
        self.assertIn('name = "AAA_gen_new"', content)
        self.assertIn("country_leader", content)  # 角色块未丢
        self.assertIn("ideology = democratic", content)


class CharacterEditorSmokeTest(unittest.TestCase):
    """角色专用编辑器 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = _mkdtemp("char_editor_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "characters"))
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        self.file = os.path.join(self.mod, "common", "characters", "AAA.txt")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write("characters = {\n"
                    "\tAAA_gen = {\n"
                    "\t\tname = \"AAA_gen\"\n"
                    "\t\tportraits = {\n"
                    "\t\t\tcivilian = {\n"
                    "\t\t\t\tlarge = GFX_P\n"
                    "\t\t\t}\n"
                    "\t\t}\n"
                    "\t}\n"
                    "}\n")

    def test_dialog_lists_and_edits_name(self):
        from character_editor_dialog import CharacterEditorDialog
        from unittest import mock
        dlg = CharacterEditorDialog(mod_path=self.mod, hoi4_path="")
        self.app.processEvents()
        self.assertEqual(dlg.list.count(), 1)
        # 修改中文名并保存
        dlg.cn_edit.setText("新名字")
        with mock.patch("character_editor_dialog.QMessageBox.information"), \
             mock.patch("character_editor_dialog.QMessageBox.warning"):
            dlg._save()
        loc_file = os.path.join(self.mod, "localisation", "simp_chinese", "generic_mod_l_simp_chinese.yml")
        self.assertTrue(os.path.isfile(loc_file))
        content = open(loc_file, "r", encoding="utf-8-sig").read()
        self.assertIn('AAA_gen: "新名字"', content)


class CharacterStructuredDataTest(unittest.TestCase):
    """批 A：角色 roles 结构化（字段/traits/desc/未知块）+ 肖像槽位无损 round-trip。"""

    def _file(self, content):
        tmp = _mkdtemp("char_struct_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        fp = os.path.join(tmp, "mod", "common", "characters", "C.txt")
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        return fp

    def test_parse_roles_structured(self):
        from character_data import load_file, role_get_field, role_get_block
        fp = self._file(
            "characters = {\n"
            "\tAAA = {\n"
            "\t\tname = \"AAA\"\n"
            "\t\tcountry_leader = {\n"
            "\t\t\tideology = democratic\n"
            "\t\t\texpire = 1.1.1.1\n"
            "\t\t\ttraits = { bold genius }\n"
            "\t\t\tdesc = AAA_ldr_desc\n"
            "\t\t}\n"
            "\t\tadvisor = {\n"
            "\t\t\tslot = political_advisor\n"
            "\t\t\tidea_token = AAA_adv\n"
            "\t\t\tallowed = { always = yes }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n")
        _h, metas, _t = load_file(fp)
        m = metas[0]
        self.assertEqual([r["role_type"] for r in m["role_entries"]],
                         ["country_leader", "advisor"])
        cl = m["role_entries"][0]
        self.assertEqual(role_get_field(cl, "ideology"), "democratic")
        self.assertEqual(cl["traits"], ["bold", "genius"])
        self.assertEqual(role_get_field(cl, "desc"), "AAA_ldr_desc")
        ad = m["role_entries"][1]
        self.assertTrue(role_get_block(ad, "allowed") is not None)

    def test_parse_portraits_slots_inline_and_multiline(self):
        from character_data import load_file
        fp = self._file(
            "characters = {\n"
            "\tAAA = {\n"
            "\t\tname = \"AAA\"\n"
            "\t\tportraits = {\n"
            "\t\t\tcivilian = { large = GFX_A small = GFX_B }\n"
            "\t\t\tarmy = {\n"
            "\t\t\t\tlarge = GFX_C\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n"
            "}\n")
        _h, metas, _t = load_file(fp)
        slots = metas[0]["portraits_slots"]
        self.assertEqual(len(slots), 3)
        self.assertEqual(slots[0]["texture"], "GFX_A")
        self.assertEqual(slots[1]["size"], "small")
        self.assertEqual(slots[2]["scope"], "army")

    def test_v2_save_roundtrip_preserves_fields_and_unknown(self):
        from character_data import load_file, save_file_v2, role_get_field, role_set_field
        src = (
            "characters = {\n"
            "\tAAA = {\n"
            "\t\tname = \"AAA\"\n"
            "\t\tcan_be_captured = no\n"
            "\t\tportraits = { civilian = { large = GFX_A } }\n"
            "\t\tcountry_leader = {\n"
            "\t\t\tideology = democratic\n"
            "\t\t\ttraits = { bold }\n"
            "\t\t\tdesc = AAA_desc\n"
            "\t\t}\n"
            "\t\tarea_defense_leader = { skill = 3 }\n"
            "\t}\n"
            "}\n")
        fp = self._file(src)
        h, metas, t = load_file(fp)
        cl = metas[0]["role_entries"][0]
        role_set_field(cl, "ideology", "communism")
        cl["traits"] = ["bold", "iron_will"]
        save_file_v2(fp, h, metas, t)
        _h2, m2, _t2 = load_file(fp)
        self.assertEqual(m2[0]["name_loc"], "AAA")
        self.assertEqual(len(m2[0]["portraits_slots"]), 1)
        cl2 = [r for r in m2[0]["role_entries"] if r["role_type"] == "country_leader"][0]
        self.assertEqual(role_get_field(cl2, "ideology"), "communism")
        self.assertEqual(cl2["traits"], ["bold", "iron_will"])
        self.assertEqual(role_get_field(cl2, "desc"), "AAA_desc")
        self.assertTrue(any(x[1] == "can_be_captured" for x in m2[0]["others_lines"]))
        self.assertEqual(
            [r["role_type"] for r in m2[0]["role_entries"]
             if r["role_type"] == "area_defense_leader"][0], "area_defense_leader")


class CharacterEditorStructSmokeTest(unittest.TestCase):
    """批 A：角色编辑器单页三栏 + 结构化 roles 编辑 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = _mkdtemp("char_editor2_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "characters"))
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        self.file = os.path.join(self.mod, "common", "characters", "AAA.txt")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write("characters = {\n"
                    "\tAAA_gen = {\n"
                    "\t\tname = \"AAA_gen\"\n"
                    "\t\tportraits = {\n"
                    "\t\t\tcivilian = { large = GFX_P }\n"
                    "\t\t}\n"
                    "\t\tcountry_leader = {\n"
                    "\t\t\tideology = democratic\n"
                    "\t\t\ttraits = { bold }\n"
                    "\t\t}\n"
                    "\t}\n"
                    "}\n")

    def _open(self):
        from character_editor_dialog import CharacterEditorDialog
        return CharacterEditorDialog(mod_path=self.mod, hoi4_path="")

    def test_roles_shown_and_column_layout(self):
        dlg = self._open()
        self.app.processEvents()
        self.assertEqual(dlg.role_list.count(), 1)
        self.assertIsNotNone(dlg.portraits_table)
        self.assertEqual(dlg.portraits_table.rowCount(), 1)
        self.assertTrue(dlg.name_loc_edit.text())
        self.assertIn("ideology", dlg.role_fields)
        dlg.close()

    def test_edit_role_field_and_save(self):
        from unittest import mock
        dlg = self._open()
        self.app.processEvents()
        dlg.role_fields["ideology"].setText("communism")
        with mock.patch("character_editor_dialog.QMessageBox.information"), \
             mock.patch("character_editor_dialog.QMessageBox.warning"):
            dlg._save()
        content = open(self.file, "r", encoding="utf-8").read()
        self.assertIn("ideology = communism", content)
        dlg.close()

    def test_add_portrait_and_save(self):
        from unittest import mock
        from PyQt6.QtWidgets import QTableWidgetItem
        dlg = self._open()
        self.app.processEvents()
        r = dlg.portraits_table.rowCount()
        dlg.portraits_table.insertRow(r)
        dlg.portraits_table.setItem(r, 0, QTableWidgetItem("navy"))
        dlg.portraits_table.setItem(r, 1, QTableWidgetItem("large"))
        dlg.portraits_table.setItem(r, 2, QTableWidgetItem("GFX_N"))
        with mock.patch("character_editor_dialog.QMessageBox.information"), \
             mock.patch("character_editor_dialog.QMessageBox.warning"):
            dlg._save()
        content = open(self.file, "r", encoding="utf-8").read()
        self.assertIn("GFX_N", content)
        self.assertIn("GFX_P", content)
        dlg.close()


class ErrorLogSubsystemTest(unittest.TestCase):
    """"错误日志：按子系统归类。"""

    def test_classify_by_subsystem(self):
        from error_log import analyze, classify_by_subsystem
        text = ("missing localisation for key X\n"
                "duplicate decision id MY_DEC\n"
                "Could not find texture gfx/interface/goals/x.dds\n")
        res = analyze(text)
        subs = classify_by_subsystem(res)
        self.assertIn("localisation", subs)
        self.assertIn("decision", subs)
        self.assertIn("gfx/gui", subs)
        total = sum(subs.values())
        self.assertEqual(total, len(res))


class ApiCoreToolTest(unittest.TestCase):
    """接口：第一批工具的 ApiCore 端点。"""

    def setUp(self):
        self.tmp = _mkdtemp("api_tools_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mod = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod, "common", "national_focus"))
        os.makedirs(os.path.join(self.mod, "gfx", "interface", "goals"))
        os.makedirs(os.path.join(self.mod, "history", "states"))
        os.makedirs(os.path.join(self.mod, "localisation", "simp_chinese"))
        self.focus = os.path.join(self.mod, "common", "national_focus", "f.txt")
        with open(self.focus, "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n id = TG_pj\n focus = { id = TG_a }\n}\n")
        with open(os.path.join(self.mod, "history", "states", "01.txt"),
                  "w", encoding="utf-8") as f:
            f.write("state = {\n\tid = 1\n\tvictory_points = { 10 2 }\n}\n")
        from api_server import ApiCore
        self.core = ApiCore(mod_path=self.mod, game_path="")
        # 建一个格式化用的临时文件（相对 mod）
        self.target_rel = "common/national_focus/ugly.txt"
        with open(os.path.join(self.mod, self.target_rel), "w", encoding="utf-8") as f:
            f.write("x = {\ny = 1\n}\n")

    def test_format_pdx(self):
        r = self.core.format_pdx({"path": self.target_rel})
        self.assertTrue(r["ok"])
        content = open(os.path.join(self.mod, self.target_rel), "r", encoding="utf-8").read()
        self.assertIn("\ty = 1", content)

    def test_vp_loc_dry_run(self):
        r = self.core.vp_loc_dry_run()
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["count"], 1)
        self.assertIn("VICTORY_POINTS_10", r["text"])

    def test_register_icon_batch_and_error_log(self):
        # 图标：放一张贴图并引用它
        open(os.path.join(self.mod, "gfx", "interface", "goals", "GFX_g.dds"), "w").close()
        with open(self.focus, "w", encoding="utf-8") as f:
            f.write("focus_tree = {\n id = TG_pj\n"
                    " focus = { id = TG_a icon = GFX_g }\n}\n")
        r = self.core.register_icon_batch({"path": "common/national_focus/f.txt", "type": "focus"})
        self.assertEqual(r["registered"], 1)
        # 错误日志
        log = os.path.join(self.mod, "error.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write("missing localisation for key X\n")
        r2 = self.core.analyze_error_log({"absolute_path": log})
        self.assertTrue(r2["ok"])
        self.assertIn("localisation", r2["subsystems"])

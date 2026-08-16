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
        """国策/科技/初始部队在顶部；分隔线不可选；其后为通用类型。"""
        from PyQt6.QtCore import Qt
        wb = self._make()
        keys = []
        for i in range(wb.type_list.count()):
            it = wb.type_list.item(i)
            keys.append((i, it.data(Qt.ItemDataRole.UserRole),
                         bool(it.flags() & Qt.ItemFlag.ItemIsSelectable)))
        self.assertEqual([k for _i, k, _s in keys[:3]],
                         ["focus", "tech", "initial_oob"])
        sep = keys[3]
        self.assertIsNone(sep[1], "分隔线无类型 data")
        self.assertFalse(sep[2], "分隔线不可选")
        self.assertIsNotNone(keys[4][1], "分隔线后应有通用类型")

    def test_clicking_separator_ignored(self):
        """点击分隔线不改变当前类型。"""
        from PyQt6.QtCore import Qt
        wb = self._make()
        wb._current_type = "focus"
        sep = wb.type_list.item(3)
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
        """detect_oob_kinds 正确识别 division/ship/air_wing。"""
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
            detect_oob_kinds("division = {\n}\nship = {\n}\nair_wing = {\n}\n"),
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


if __name__ == "__main__":
    unittest.main()

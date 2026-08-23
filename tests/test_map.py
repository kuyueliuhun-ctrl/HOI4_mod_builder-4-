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


class StateResTest(unittest.TestCase):
    """state 资源/VP/manpower/州名 结构化读写。"""

    def _content(self):
        return ("state = {\n"
                "\tid = 1\n"
                "\tname = \"STATE_1\"\n"
                "\tmanpower = 100\n"
                "\tresources = {\n"
                "\t\tsteel = 6\n"
                "\t}\n"
                "\tstate_category = town\n"
                "\thistory = {\n"
                "\t\towner = FRA\n"
                "\t\tvictory_points = { 10 1 }\n"
                "\t}\n"
                "}\n")

    def test_parse_resources(self):
        from state_loader import StateData
        import tempfile, os
        tmp = _mkdtemp("dsh_stateres_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        d = os.path.join(tmp, "history", "states")
        os.makedirs(d)
        fp = os.path.join(d, "1-test.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(self._content())
        sd = StateData(tmp, "")
        st = sd.states.get(1)
        self.assertIsNotNone(st)
        self.assertEqual(st["resources"], {"steel": 6})

    def test_write_resources_vp_name_manpower(self):
        from state_build_ops import (
            set_state_resources_in_content,
            set_state_victory_points_in_content,
            set_state_manpower_in_content,
            set_state_name_in_content,
        )
        content = self._content()
        c = set_state_resources_in_content(
            content, 1, {"steel": 8, "oil": 2})
        self.assertIn("steel = 8", c)
        self.assertIn("oil = 2", c)
        c = set_state_victory_points_in_content(c, 1, [(10, 2), (20, 3)])
        self.assertIn("victory_points = { 10 2 20 3 }", c)
        c = set_state_manpower_in_content(c, 1, 200)
        self.assertIn("manpower = 200", c)
        c = set_state_name_in_content(c, 1, "STATE_9")
        self.assertIn('name = "STATE_9"', c)



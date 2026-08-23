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



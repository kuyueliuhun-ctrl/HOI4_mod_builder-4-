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

    def test_load_equipment_stats_captures_build_cost_ic(self):
        """装备块应采集 build_cost_ic / convert_cost_ic（P2.5 IC 估算）。"""
        from oob_loader import load_equipment_stats
        mod = _mkdtemp("dsh_ic_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "units", "equipment"),
                    exist_ok=True)
        with open(os.path.join(mod, "common", "units", "equipment",
                               "infantry.txt"), "w", encoding="utf-8") as f:
            f.write('equipments = {\n'
                    '\tinfantry_equipment_0 = {\n'
                    '\t\tsoft_attack = 6\n'
                    '\t\tbuild_cost_ic = 4\n'
                    '\t\tconvert_cost_ic = 1\n'
                    '\t}\n'
                    '}\n')
        eq = load_equipment_stats(mod, "")
        self.assertEqual(eq["infantry_equipment_0"]["build_cost_ic"], 4.0)
        self.assertEqual(eq["infantry_equipment_0"]["convert_cost_ic"], 1.0)

    def test_division_ic_cost_math(self):
        """division_ic_cost：need 数量 × 装备 build_cost_ic 求和。"""
        from oob_loader import division_ic_cost, DivisionTemplate
        sub = {
            "infantry": {"need": {"infantry_equipment": 100.0}},
            "engineer": {"need": {"support_equipment": 50.0}},
        }
        eq = {"infantry_equipment_0": {"build_cost_ic": 4.0},
              "support_equipment_0": {"build_cost_ic": 2.0}}
        tpl = DivisionTemplate("T", regiments=[("infantry", 0, 0)],
                               support=[("engineer", 0, 0)])
        r = division_ic_cost(tpl, sub, eq)
        self.assertEqual(r["total_ic"], 100 * 4.0 + 50 * 2.0)
        self.assertEqual(r["equipment"]["infantry_equipment"],
                         {"count": 100.0, "ic": 400.0})
        self.assertEqual(r["equipment"]["support_equipment"],
                         {"count": 50.0, "ic": 100.0})
        # 未知装备定义 → IC 计 0 不崩溃
        r2 = division_ic_cost(tpl, {"infantry": {"need": {"weird_eq": 10}}},
                              {})
        self.assertEqual(r2["total_ic"], 0.0)


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
                    '\tmodules = {\n'
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


class CharacterDescTest(unittest.TestCase):
    """角色顶层 desc 键提取/写回。"""

    def _write(self, content):
        mod = _mkdtemp("dsh_chardesc_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "characters")
        os.makedirs(d)
        fp = os.path.join(d, "TST.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        return mod, fp

    def test_parse_and_save_roundtrip(self):
        from character_data import load_file, save_file_v2
        mod, fp = self._write(
            "characters = {\n"
            "\tTST_leader = {\n"
            "\t\tname = \"TST_leader\"\n"
            "\t\tdesc = \"TST_leader_desc\"\n"
            "\t}\n"
            "}\n")
        header, metas, tail = load_file(fp)
        self.assertEqual(metas[0]["desc_loc"], "TST_leader_desc")
        save_file_v2(fp, header, metas, tail)
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('desc = "TST_leader_desc"', content)


class CharacterRouteTest(unittest.TestCase):
    """角色文件路由映射。"""

    def test_route_contains_character(self):
        from app_routes import find_route
        norm, route = find_route("E:/mod/common/characters/PRC.txt")
        self.assertIsNotNone(route)
        self.assertEqual(route[0], "common/characters")


class CharacterPortraitPreviewTest(unittest.TestCase):
    """角色编辑器肖像表带预览列。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_preview_column_present(self):
        from character_editor_dialog import CharacterEditorDialog
        mod = _mkdtemp("dsh_charprev_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "characters")
        os.makedirs(d)
        with open(os.path.join(d, "TST.txt"), "w", encoding="utf-8") as f:
            f.write("characters = {\n\tTST_leader = {\n\t\tname = \"TST_leader\"\n"
                    "\t\tportraits = { civilian = { large = GFX_P } }\n\t}\n}\n")
        dlg = CharacterEditorDialog(mod_path=mod)
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.portraits_table.columnCount(), 4)
        self.assertEqual(dlg.portraits_table.rowCount(), 1)
        self.assertIsNotNone(dlg.portraits_table.item(0, 3))
        dlg.close()


class TechLayoutTest(unittest.TestCase):
    """科技树布局：同层不重叠、子继承父中位。"""

    def _techs(self):
        return {
            "a": {"folder": "f", "leads_to": ["b", "c"]},
            "b": {"folder": "f", "leads_to": ["d"]},
            "c": {"folder": "f", "leads_to": []},
            "d": {"folder": "f", "leads_to": []},
        }

    def test_layout_no_same_layer_overlap_and_parent_median(self):
        from tech_view import layout_tech_trees, GRID_X
        techs = self._techs()
        layout = layout_tech_trees(techs, set(techs))
        pos = layout["f"]
        # 同一层 x 间距至少 1 槽
        by_depth = {}
        for tid, (x, y) in pos.items():
            by_depth.setdefault(y, []).append(x)
        for y, xs in by_depth.items():
            xs_sorted = sorted(xs)
            for i in range(1, len(xs_sorted)):
                self.assertGreaterEqual(xs_sorted[i] - xs_sorted[i - 1],
                                        GRID_X - 1)
        # a 的 x 应介于 b、c 之间（中位）
        self.assertGreaterEqual(pos["a"][0], min(pos["b"][0], pos["c"][0]))
        self.assertLessEqual(pos["a"][0], max(pos["b"][0], pos["c"][0]))


class EventDataTest(unittest.TestCase):
    """事件数据层解析。"""

    def _make(self):
        mod = _mkdtemp("dsh_evt_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "events")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write("add_namespace = TST\n"
                    "country_event = {\n"
                    "\tid = TST.1\n"
                    "\ttitle = TST_TITLE\n"
                    "\tdesc = TST_DESC\n"
                    "\tpicture = GFX_event_tst\n"
                    "\toption = { name = TST_OPT }\n"
                    "\toption = { name = TST_OPT2 }\n"
                    "}\n")
        return mod

    def test_load_event_entities(self):
        from event_data import load_event_entities
        mod = self._make()
        events = load_event_entities(mod, "")
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["id"], "TST.1")
        self.assertEqual(e["type"], "country_event")
        self.assertEqual(e["title"], "TST_TITLE")
        self.assertEqual(e["desc"], "TST_DESC")
        self.assertEqual(e["option_count"], 2)
        self.assertEqual(e["namespaces"], ["TST"])


class EventEditorSmokeTest(unittest.TestCase):
    """事件编辑器 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make(self):
        mod = _mkdtemp("dsh_evtui_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "events")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write("add_namespace = TST\n"
                    "country_event = {\n"
                    "\tid = TST.1\n"
                    "\ttitle = TST_TITLE\n"
                    "\tdesc = TST_DESC\n"
                    "\tpicture = GFX_event_tst\n"
                    "\toption = { name = TST_OPT }\n"
                    "}\n")
        return mod

    def test_list_and_form_load(self):
        from event_editor_dialog import EventEditorDialog
        mod = self._make()
        dlg = EventEditorDialog(mod_path=mod)
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 1)
        self.assertEqual(dlg.id_edit.text(), "TST.1")
        self.assertEqual(dlg.title_edit.text(), "TST_TITLE")
        self.assertEqual(dlg.options_label.text(), "1")
        dlg.close()


class TechDataTest(unittest.TestCase):
    """科技数据层解析。"""

    def _make(self):
        mod = _mkdtemp("dsh_techd_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "technologies")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write("technologies = {\n"
                    "\tinfa = {\n"
                    "\t\tstart_year = 1936\n"
                    "\t\tresearch_cost = 0.5\n"
                    "\t\tcategories = { infantry }\n"
                    "\t\tfolder = { name = infantry position = 0 }\n"
                    "\t\tpath = { leads_to_tech = infb research_cost_coeff = 0.5 }\n"
                    "\t\tsub_technologies = { infa_1 infa_2 }\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_load_tech_entities(self):
        from tech_data import load_tech_entities
        mod = self._make()
        techs = load_tech_entities(mod, "")
        self.assertIn("infa", techs)
        t = techs["infa"]
        self.assertEqual(t["start_year"], "1936")
        self.assertEqual(t["research_cost"], "0.5")
        self.assertEqual(t["folder"], "infantry")
        self.assertIn("infantry", t["categories"])
        self.assertIn("infb", t["leads_to_tech"])
        self.assertIn("infa_1", t["sub_technologies"])


class TechEditorSmokeTest(unittest.TestCase):
    """科技编辑器 offscreen 冒烟。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _make(self):
        mod = _mkdtemp("dsh_techui_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        d = os.path.join(mod, "common", "technologies")
        os.makedirs(d)
        with open(os.path.join(d, "test.txt"), "w", encoding="utf-8") as f:
            f.write("technologies = {\n"
                    "\tinfa = {\n"
                    "\t\tstart_year = 1936\n"
                    "\t\tresearch_cost = 0.5\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_list_and_form_load(self):
        from tech_editor_dialog import TechEditorDialog
        mod = self._make()
        dlg = TechEditorDialog(mod_path=mod)
        dlg.show()
        self.app.processEvents()
        self.assertEqual(dlg.sidebar.list.count(), 1)
        self.assertEqual(dlg.id_edit.text(), "infa")
        self.assertEqual(dlg.start_year_edit.text(), "1936")
        dlg.close()


class Terrain3Test(unittest.TestCase):
    """地形三项（movement/attack/defence）解析与汇总。"""

    def _make_sub(self):
        mod = _mkdtemp("dsh_terr3_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "units"), exist_ok=True)
        with open(os.path.join(mod, "common", "units", "inf.txt"),
                  "w", encoding="utf-8") as f:
            f.write("sub_units = {\n"
                    "\tinfantry = {\n"
                    "\t\tabbreviation = INF\n"
                    "\t\tforest = { movement = 0.2 attack = -0.1 defence = 0.1 }\n"
                    "\t}\n"
                    "}\n")
        from oob_loader import load_sub_units
        return load_sub_units(mod, "")["infantry"]

    def test_terrain_full_parsed(self):
        inf = self._make_sub()
        self.assertEqual(inf["terrain_full"]["forest"]["movement"], 0.2)
        self.assertEqual(inf["terrain_full"]["forest"]["attack"], -0.1)
        self.assertEqual(inf["terrain_full"]["forest"]["defence"], 0.1)


class SubUnitEditorTest(unittest.TestCase):
    """兵种保存 roundtrip。"""

    def _make(self):
        mod = _mkdtemp("dsh_subed_")
        self.addCleanup(shutil.rmtree, mod, ignore_errors=True)
        os.makedirs(os.path.join(mod, "common", "units"), exist_ok=True)
        with open(os.path.join(mod, "common", "units", "inf.txt"),
                  "w", encoding="utf-8") as f:
            f.write("sub_units = {\n"
                    "\tinfantry = {\n"
                    "\t\tabbreviation = INF\n"
                    "\t\tcombat_width = 2\n"
                    "\t\tneed = { infantry_equipment = 100 }\n"
                    "\t}\n"
                    "}\n")
        return mod

    def test_save_sub_unit_fields(self):
        from oob_loader import save_sub_unit
        mod = self._make()
        fp = save_sub_unit(mod, "", "infantry",
                           fields={"combat_width": 3},
                           need={"infantry_equipment": 120})
        self.assertIsNotNone(fp)
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("combat_width = 3", content)
        self.assertIn("infantry_equipment = 120", content)

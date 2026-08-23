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
            [k for _i, k, _s in keys[:14]],
            ["character", "focus", "event", "tech", "initial_oob", "bop",
             "ai_strategy_plans", "ai_strategy", "ai_division", "ai_areas",
             "ai_equipment", "ai_faction_theaters", "ai_focuses", "ai_navy"])
        sep = keys[14]
        self.assertIsNone(sep[1], "分隔线无类型 data")
        self.assertFalse(sep[2], "分隔线不可选")
        self.assertIsNotNone(keys[15][1], "分隔线后应有通用类型")

    def test_clicking_separator_ignored(self):
        """点击分隔线不改变当前类型。"""
        from PyQt6.QtCore import Qt
        wb = self._make()
        wb._current_type = "focus"
        sep = wb.type_list.item(14)
        wb._on_type_clicked(sep)
        self.assertEqual(wb._current_type, "focus", "分隔线点击应被忽略")



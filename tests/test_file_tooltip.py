"""file_tooltip 助手与 EntityListSidebar 悬停文件提示测试。"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class FileTooltipHelper(unittest.TestCase):
    def _mk(self, root):
        os.makedirs(root, exist_ok=True)
        return root

    def test_mod_origin(self):
        from ai_ui_common import file_tooltip
        mod = self._mk("/tmp/ft_mod_a")
        ent = {"rel": "common/x/y.txt",
               "file": os.path.join(mod, "common", "x", "y.txt")}
        tip = file_tooltip(ent, mod, "/tmp/ft_game_a")
        self.assertIn("文件：common/x/y.txt", tip)
        self.assertIn("来源：mod", tip)

    def test_game_origin(self):
        from ai_ui_common import file_tooltip
        game = self._mk("/tmp/ft_game_b")
        ent = {"file": os.path.join(game, "common", "a.txt")}
        tip = file_tooltip(ent, "/tmp/ft_mod_b", game)
        self.assertIn("来源：游戏", tip)
        self.assertIn("文件：%s" % os.path.join(game, "common", "a.txt"), tip)

    def test_missing_info_returns_none(self):
        from ai_ui_common import file_tooltip
        self.assertIsNone(file_tooltip({"id": "x"}))
        self.assertIsNone(file_tooltip("not-a-dict"))
        self.assertIsNone(file_tooltip(None))


class SidebarTooltips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtCore import Qt
        cls.Qt = Qt
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _sidebar(self):
        from ai_ui_common import EntityListSidebar
        return EntityListSidebar("实体", None, enable_crud=False)

    def _tip(self, sidebar, eid):
        for i in range(sidebar.list.count()):
            it = sidebar.list.item(i)
            if it.data(self.Qt.ItemDataRole.UserRole) == eid:
                return it.toolTip()
        return None

    def test_triple_and_pair_entries(self):
        sb = self._sidebar()
        sb.set_entities([
            ("a", "甲", "文件：common/a.txt"),
            ("b", "乙"),
        ])
        self.assertIn("common/a.txt", self._tip(sb, "a"))
        self.assertEqual(self._tip(sb, "b"), "乙")

    def test_tooltips_kwarg(self):
        sb = self._sidebar()
        sb.set_entities([("a", "甲"), ("b", "乙")],
                        tooltips=[None, "文件：b.txt"])
        self.assertEqual(self._tip(sb, "a"), "甲")
        self.assertIn("b.txt", self._tip(sb, "b"))

    def test_filter_keeps_tooltip(self):
        sb = self._sidebar()
        sb.set_entities([("a", "甲", "文件：a.txt"), ("b", "乙", "文件：b.txt")])
        sb._apply_filter("甲")
        self.assertEqual(sb.list.count(), 1)
        self.assertIn("a.txt", sb.list.item(0).toolTip())


if __name__ == "__main__":
    unittest.main()

"""B0 公共组件测试：ui_widgets.py 基础 roundtrip。"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class UiWidgetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_block_cn_dict(self):
        from ui_widgets import BLOCK_CN, _cn
        self.assertEqual(_cn("visible"), "可见性")
        self.assertIn("available", BLOCK_CN)
        self.assertEqual(_cn("unknown_key_xyz"), "unknown_key_xyz")
        self.assertGreaterEqual(len(BLOCK_CN), 50)

    def test_source_badge(self):
        from ui_widgets import source_badge
        self.assertEqual(source_badge("mod").text(), "mod 改写")
        self.assertEqual(source_badge("game").text(), "本体")
        self.assertEqual(source_badge("").text(), "")

    def test_loc_edit(self):
        from ui_widgets import LocEdit
        w = LocEdit("visible", "可见性")
        self.assertIn("可见性", w.key_label.text())
        self.assertEqual(w.text(), "可见性")
        w.setText("新值")
        self.assertEqual(w.text(), "新值")

    def test_block_tree_list_roundtrip(self):
        from ui_widgets import BlockTreeList
        tree = BlockTreeList()
        tree.add_item("visible", "yes", "可见性")
        tree.add_item("available", "", "可用条件")
        data = tree.data()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["key"], "visible")
        self.assertEqual(data[0]["value"], "yes")

    def test_ref_picker_warn(self):
        from ui_widgets import RefPicker
        picker = RefPicker(["GER", "SOV"])
        picker.setValue("FRA")
        self.assertEqual(picker.value(), "FRA")
        self.assertEqual(picker.warn.text(), "⚠ 未找到")
        picker.setValue("GER")
        self.assertEqual(picker.warn.text(), "")

    def test_weight_table_roundtrip(self):
        from ui_widgets import WeightTable
        table = WeightTable()
        table.set_rows([("soft_attack", "10"), ("hard_attack", "5")])
        self.assertEqual(table.rows(), [("soft_attack", "10"),
                                        ("hard_attack", "5")])
        table.add_row("new", "1")
        self.assertEqual(table.rowCount(), 3)

    def test_order_row_list(self):
        from ui_widgets import OrderRowList
        lst = OrderRowList()
        lst.set_order(["A", "B", "C"])
        self.assertEqual(lst.order(), ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
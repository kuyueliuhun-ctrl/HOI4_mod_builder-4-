"""契约测试：FocusTreeModel.data 各 role 的展示逻辑。"""

from __future__ import annotations

import sys
import os
import unittest

from PyQt6.QtCore import Qt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


class FocusTreeModelDataTest(unittest.TestCase):
    def _make_model(self):
        from tree_node import TreeNode
        from tree_model import FocusTreeModel
        root = TreeNode("block", "focus")
        root.add_child(TreeNode("value", "id", "my_focus"))
        root.add_child(TreeNode("value", "cost", "10"))
        root.add_child(TreeNode("block", "available"))
        return FocusTreeModel(root)

    def test_display_edit_tooltip_and_user_roles(self):
        model = self._make_model()
        idx = model.index(0, 0)
        self.assertEqual(
            model.data(idx, Qt.ItemDataRole.DisplayRole), "📄 id = my_focus")
        self.assertEqual(
            model.data(idx, Qt.ItemDataRole.EditRole), "my_focus")
        tooltip = model.data(idx, Qt.ItemDataRole.ToolTipRole)
        self.assertIn("类型:", tooltip)
        self.assertIn("键: id", tooltip)
        self.assertIs(
            model.data(idx, Qt.ItemDataRole.UserRole), idx.internalPointer())

    def test_display_value_without_key(self):
        from tree_node import TreeNode
        from tree_model import FocusTreeModel
        root = TreeNode("block", "focus")
        root.add_child(TreeNode("value", "", "plain_value"))
        model = FocusTreeModel(root)
        idx = model.index(0, 0)
        self.assertEqual(model.data(idx, Qt.ItemDataRole.DisplayRole), "📄 plain_value")


if __name__ == "__main__":
    unittest.main()
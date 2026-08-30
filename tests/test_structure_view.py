# -*- coding: utf-8 -*-
"""结构体展示组件（StructureView）测试。

覆盖：
- 块=列表行、缩进嵌套渲染（行数/层级/块摘要），默认全部展开；
- 本地化为树形编辑器同款样式：DisplayRole 内联 `键--中文` / `值--中文值`，
  EditRole 恒为原始键/值（编辑与展示分离）；
- 双击语义对应的写回：键改名、值改值（含比较语句节点）、raw_lines 失效；
- 块交互：双击块字段（键列）改名写回、双击块行值列展开/收起、键列双击不收起；
- 添加功能（复刻树形编辑器）：add_node 块内插入/顶层插入、非法父目标拒绝；
- 真实数据冒烟：游戏 MIO 组织文件 载入→序列化→重解析 层级一致。
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt6.QtCore import QModelIndex, QRect, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QAbstractItemView,
    QApplication,
    QPlainTextEdit,
    QStyleOptionViewItem,
)

from structure_view import StructureView  # noqa: E402
from tree_node import TreeNode, parse_pdx_text_to_nodes  # noqa: E402

GAME = "/mnt/e/SteamLibrary/steamapps/common/Hearts of Iron IV"

SAMPLE = """\
GER_generic_mio_organization = {
\tname = GER_mio_name
\ticon = gfx/interface/illustrations/mio/mio_tank.png
\tequipment = {
\t\ttype = char_1_type
\t\tcost = 1.5
\t}
\ttrait = {
\t\ttoken = my_trait
\t\tname = my_trait_loc
\t\tposition = { x = 2 y = 1 }
\t\ton_complete = { }
\t}
\tinitial_trait = { visible = { has_dlc = "Arms Against Tyranny" } }
\tavailable = {
\t\tnum_of_military_factories > 5
\t}
}
"""


class _StubTranslator:
    """测试替身：与 GuiTranslator.translate_node 相同的接口契约。

    键/值无翻译时原样返回（与 GuiTranslator 行为一致）。
    """

    def __init__(self, key_map=None, val_map=None):
        self.km = key_map or {}
        self.vm = val_map or {}

    def translate_node(self, key, value=None):
        cn_key = self.km.get(key, key)
        if value:
            cn_val = self.vm.get(value, value)
        else:
            cn_val = value or ""
        return cn_key, cn_val


def _items(view):
    return [view.topLevelItem(i) for i in range(view.topLevelItemCount())]


class StructureViewRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = StructureView()
        self.view.load_text(SAMPLE)

    def test_top_level_and_nesting(self):
        items = _items(self.view)
        self.assertEqual(len(items), 1)
        org = items[0]
        # 顶层组织块的子条目：name/icon/equipment/trait/initial_trait/available
        self.assertEqual(org.childCount(), 6)
        keys = [org.child(j).text(0) for j in range(6)]
        self.assertEqual(keys, ["name", "icon", "equipment", "trait",
                                "initial_trait", "available"])
        # 缩进嵌套：equipment 块有子条目
        equip = org.child(2)
        self.assertEqual(equip.text(1), "{ … } · 2 项")
        self.assertEqual(equip.childCount(), 2)
        self.assertEqual(equip.child(0).text(0), "type")
        self.assertEqual(equip.child(0).text(1), "char_1_type")

    def test_two_columns_no_loc_column(self):
        """本地化改为内联样式后，视图为两列（键/值）。"""
        self.assertEqual(self.view.columnCount(), 2)
        self.assertEqual(self.view.headerItem().text(0), "键")
        self.assertEqual(self.view.headerItem().text(1), "值")

    def test_block_rows_marked_and_value_rows_plain(self):
        org = _items(self.view)[0]
        trait = org.child(3)
        self.assertEqual(trait.text(1), "{ … } · 4 项")
        name_row = org.child(0)
        self.assertEqual(name_row.text(1), "GER_mio_name")
        # position 嵌套块
        pos = trait.child(2)
        self.assertEqual(pos.text(0), "position")
        self.assertEqual(pos.child(0).text(0), "x")
        self.assertEqual(pos.child(0).text(1), "2")

    def test_statement_node_rendered(self):
        org = _items(self.view)[0]
        avail = org.child(5)
        self.assertEqual(avail.text(0), "available")
        self.assertEqual(avail.text(1), "{ … } · 1 项")
        stmt = avail.child(0)
        self.assertEqual(stmt.text(0), "·")  # 比较语句无键名
        self.assertEqual(stmt.text(1), "num_of_military_factories > 5")

    def test_to_pdx_roundtrip_child_counts(self):
        text = self.view.to_pdx_text()
        nodes = parse_pdx_text_to_nodes(text)
        self.assertEqual(len(nodes), 1)
        org = nodes[0]
        self.assertEqual(len(org.children), 6)
        equip = org.children[2]
        self.assertEqual([c.key for c in equip.children], ["type", "cost"])
        # 比较语句经 序列化→重解析 仍是语句节点
        avail = org.children[5]
        self.assertEqual(len(avail.children), 1)
        self.assertEqual(avail.children[0].value, "num_of_military_factories > 5")


class StructureViewInlineLocTest(unittest.TestCase):
    """树形编辑器同款本地化：DisplayRole 内联 --中文，EditRole 原始文本。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self):
        tr = _StubTranslator(
            key_map={"name": "名称", "equipment": "装备", "token": "标识"},
            val_map={"GER_mio_name": "德国组织名", "my_trait": "我的特质"},
        )
        view = StructureView(translator=tr)
        view.load_text(SAMPLE)
        return view

    def test_value_row_key_and_value_inline_translation(self):
        org = _items(self._view())[0]
        name_row = org.child(0)
        self.assertEqual(name_row.text(0), "name--名称")
        self.assertEqual(name_row.text(1), "GER_mio_name--德国组织名")
        # 无翻译的键值原样
        icon_row = org.child(1)
        self.assertEqual(icon_row.text(0), "icon")
        self.assertEqual(icon_row.text(1),
                         "gfx/interface/illustrations/mio/mio_tank.png")

    def test_block_key_inline_translation(self):
        org = _items(self._view())[0]
        equip = org.child(2)
        self.assertEqual(equip.text(0), "equipment--装备")  # 块键同样带中文
        self.assertEqual(equip.text(1), "{ … } · 2 项")     # 块值列是摘要不受影响

    def test_trait_token_value_translation(self):
        org = _items(self._view())[0]
        token_row = org.child(3).child(0)
        self.assertEqual(token_row.text(0), "token--标识")
        self.assertEqual(token_row.text(1), "my_trait--我的特质")

    def test_statement_and_numbers_untranslated(self):
        view = self._view()
        org = _items(view)[0]
        stmt = org.child(5).child(0)
        self.assertEqual(stmt.text(1), "num_of_military_factories > 5")
        cost = org.child(2).child(1)
        self.assertEqual(cost.text(1), "1.5")

    def test_edit_role_returns_raw_text(self):
        """编辑器里永远是原始键/值（不带 --中文 后缀）。"""
        view = self._view()
        org = _items(view)[0]
        name_row = org.child(0)
        self.assertEqual(name_row.data(0, Qt.ItemDataRole.EditRole), "name")
        self.assertEqual(name_row.data(1, Qt.ItemDataRole.EditRole), "GER_mio_name")
        equip = org.child(2)
        self.assertEqual(equip.data(0, Qt.ItemDataRole.EditRole), "equipment")

    def test_translator_hot_swap_refreshes_display(self):
        view = StructureView()
        view.load_text(SAMPLE)
        org = _items(view)[0]
        self.assertEqual(org.child(0).text(0), "name")
        view.set_translator(_StubTranslator(key_map={"name": "名称"}))
        self.assertEqual(org.child(0).text(0), "name--名称")


class StructureViewEditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = StructureView()
        self.view.load_text(SAMPLE)

    def _org_item(self):
        return _items(self.view)[0]

    def test_editor_commit_via_setdata(self):
        """编辑器提交全链路：EditRole setData → 节点写回 → 展示层现算刷新。"""
        org = self._org_item()
        name_row = org.child(0)
        node = name_row.node
        name_row.setData(StructureView.COL_KEY,
                         Qt.ItemDataRole.EditRole, "renamed_key")
        self.assertEqual(node.key, "renamed_key")
        self.assertEqual(node.raw_lines, [])
        self.assertEqual(name_row.text(0), "renamed_key")  # 展示层跟随
        self.assertIn("renamed_key = GER_mio_name", self.view.to_pdx_text())

    def test_value_edit_via_setdata(self):
        org = self._org_item()
        name_row = org.child(0)
        node = name_row.node
        name_row.setData(StructureView.COL_VALUE,
                         Qt.ItemDataRole.EditRole, "new_value_here")
        self.assertEqual(node.value, "new_value_here")
        self.assertIn("name = new_value_here", self.view.to_pdx_text())

    def test_commit_edit_noop_on_same(self):
        org = self._org_item()
        node = org.child(0).node
        self.assertFalse(self.view._commit_node_edit(node, StructureView.COL_KEY,
                                                     "name"))

    def test_statement_edit_updates_raw_lines(self):
        org = self._org_item()
        stmt_item = org.child(5).child(0)
        node = stmt_item.node
        new_stmt = "num_of_military_factories > 10"
        stmt_item.setData(StructureView.COL_VALUE,
                          Qt.ItemDataRole.EditRole, new_stmt)
        self.assertEqual(node.raw_lines, [new_stmt])
        self.assertIn(new_stmt, self.view.to_pdx_text())

    def test_block_key_rename_writeback(self):
        """双击块字段改名：块名写回，子条目原样保留。"""
        org = self._org_item()
        equip = org.child(2)
        node = equip.node
        equip.setData(StructureView.COL_KEY,
                      Qt.ItemDataRole.EditRole, "equipment_new")
        self.assertEqual(node.key, "equipment_new")
        out = self.view.to_pdx_text()
        self.assertIn("equipment_new = {", out)
        self.assertIn("type = char_1_type", out)   # 子条目保留
        self.assertNotIn("\tequipment = {", out)

    def test_blocks_expanded_by_default(self):
        """组件默认展开：载入后所有块行均为展开态。"""
        org = self._org_item()
        self.assertTrue(org.isExpanded())
        self.assertTrue(org.child(2).isExpanded())              # equipment 块
        self.assertTrue(org.child(3).isExpanded())              # trait 块
        self.assertTrue(org.child(3).child(2).isExpanded())     # position 嵌套块

    def test_block_value_double_click_toggles_expansion(self):
        """双击块行值列：展开 ↔ 收起。"""
        org = self._org_item()
        equip = org.child(2)
        self.assertTrue(equip.isExpanded())  # 默认展开
        self.view._on_double_clicked(equip, StructureView.COL_VALUE)
        self.assertFalse(equip.isExpanded())
        self.view._on_double_clicked(equip, StructureView.COL_VALUE)
        self.assertTrue(equip.isExpanded())

    def test_block_key_double_click_keeps_expanded(self):
        """双击块字段（键列）走行内改名，不触发收起。"""
        org = self._org_item()
        equip = org.child(2)
        self.view._on_double_clicked(equip, StructureView.COL_KEY)
        self.assertTrue(equip.isExpanded())
        self.assertEqual(self.view.state(),
                         QAbstractItemView.State.EditingState)  # 编辑器已打开

    def test_structure_changed_signal_on_commit(self):
        org = self._org_item()
        node = org.child(0).node
        fired = []
        self.view.structureChanged.connect(lambda: fired.append(1))
        self.view._commit_node_edit(node, StructureView.COL_VALUE, "GER_mio_name")
        self.assertEqual(fired, [])  # 同文本不写回不触发
        self.view._commit_node_edit(node, StructureView.COL_VALUE, "changed_value")
        self.assertEqual(len(fired), 1)

    def _open_editor(self, row, col):
        """打开行内编辑并返回编辑器（离屏下焦点不可用，从子控件中查找）。"""
        self.view.editItem(row, col)
        editors = self.view.viewport().findChildren(QPlainTextEdit)
        self.assertTrue(editors, "编辑器未创建")
        return editors[-1]

    def test_real_editor_commit_and_close(self):
        """真实编辑器全链路：打开→输入→Enter 提交→关闭。

        回归：提交时 dataChanged 重入曾导致退出编辑直接崩溃（现已延迟刷新）。
        """
        org = self._org_item()
        row = org.child(0)
        node = row.node
        editor = self._open_editor(row, StructureView.COL_VALUE)
        editor.setPlainText("edited_value")
        QTest.keyClick(editor, Qt.Key.Key_Return)  # 经委托 eventFilter 提交
        self.assertEqual(node.value, "edited_value")
        self.assertIn("name = edited_value", self.view.to_pdx_text())
        self.assertNotEqual(self.view.state(),
                            QAbstractItemView.State.EditingState)  # 编辑器已关闭

    def test_real_editor_escape_reverts(self):
        """Esc 取消编辑：节点数据不变。"""
        org = self._org_item()
        row = org.child(0)
        node = row.node
        editor = self._open_editor(row, StructureView.COL_VALUE)
        editor.setPlainText("junk_text")
        QTest.keyClick(editor, Qt.Key.Key_Escape)
        self.assertEqual(node.value, "GER_mio_name")  # 未写入
        self.assertIn("name = GER_mio_name", self.view.to_pdx_text())

    def test_editor_geometry_taller_than_row(self):
        """编辑框加高：比单元格行高多出 EXTRA_LINES 行，长内容完整可见。"""
        delegate = self.view.itemDelegate()
        editor = delegate.createEditor(self.view, QStyleOptionViewItem(),
                                       QModelIndex())
        opt = QStyleOptionViewItem()
        opt.rect = QRect(10, 100, 200, 22)
        delegate.updateEditorGeometry(editor, opt, QModelIndex())
        self.assertGreater(editor.height(), 40)
        editor.deleteLater()

    def test_editor_wordwrap_enabled(self):
        """编辑框支持自动换行：长 token 不再横向截断。"""
        delegate = self.view.itemDelegate()
        editor = delegate.createEditor(self.view, QStyleOptionViewItem(),
                                       QModelIndex())
        self.assertEqual(editor.wordWrapMode(), __import__(
            "PyQt6.QtGui", fromlist=["QTextOption"]).QTextOption.WrapMode.WrapAnywhere)
        editor.deleteLater()


class StructureViewAddTest(unittest.TestCase):
    """添加功能（复刻树形编辑器 NodeEditDialog 流程）。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = StructureView()
        self.view.load_text(SAMPLE)

    def test_add_node_into_block(self):
        org = _items(self.view)[0]
        equip = org.child(2)
        fired = []
        self.view.structureChanged.connect(lambda: fired.append(1))
        item = self.view.add_node(TreeNode("value", "new_field", "yes"), equip)
        self.assertIsNotNone(item)
        node = equip.node
        self.assertEqual([c.key for c in node.children], ["type", "cost", "new_field"])
        self.assertEqual(equip.childCount(), 3)
        self.assertEqual(equip.text(1), "{ … } · 3 项")   # 摘要同步
        self.assertIn("new_field = yes", self.view.to_pdx_text())
        self.assertEqual(fired, [1])

    def test_add_block_node_with_children(self):
        org = _items(self.view)[0]
        item = self.view.add_node(
            TreeNode("block", "extra_block"), org.child(2))
        self.assertEqual(item.childCount(), 0)
        self.assertTrue(org.child(2).isExpanded())  # 插入后父块保持展开
        self.assertIn("extra_block = { }", self.view.to_pdx_text())

    def test_add_top_level_node(self):
        item = self.view.add_node(TreeNode("value", "top_key", "top_val"), None)
        self.assertIsNotNone(item)
        self.assertEqual(self.view.topLevelItemCount(), 2)
        self.assertIn("top_key = top_val", self.view.to_pdx_text())

    def test_add_rejects_non_block_parent(self):
        org = _items(self.view)[0]
        before = self.view.to_pdx_text()
        self.assertIsNone(self.view.add_node(
            TreeNode("value", "x", "1"), org.child(0)))  # 值行不是合法父目标
        self.assertEqual(self.view.to_pdx_text(), before)

    def test_add_rejects_non_node(self):
        self.assertIsNone(self.view.add_node("not a node", None))


class StructureViewRealDataTest(unittest.TestCase):
    """真实数据冒烟：游戏 MIO 组织文件 载入→序列化→重解析 层级一致。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_real_mio_file_roundtrip(self):
        path = os.path.join(GAME, "common", "military_industrial_organization",
                            "organizations", "00_generic_organization.txt")
        if not os.path.isfile(path):
            self.skipTest("游戏数据不存在：%s" % path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        view = StructureView()
        view.load_text(text)
        self.assertGreater(view.topLevelItemCount(), 0)
        # 层级一致：编辑不改动的情况下，序列化→重解析 的节点树与视图行数一致
        nodes = parse_pdx_text_to_nodes(view.to_pdx_text())
        self.assertEqual(len(nodes), view.topLevelItemCount())
        for node, item in zip(nodes, _items(view)):
            self.assertEqual(len(node.children), item.childCount())


if __name__ == "__main__":
    unittest.main()

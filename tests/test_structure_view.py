# -*- coding: utf-8 -*-
"""结构体展示组件（StructureView）测试。

覆盖：
- 块=列表行、缩进嵌套渲染（行数/层级/块摘要）；
- 双击语义对应的写回：键改名、值改值（含比较语句节点）、raw_lines 失效；
- 整块编辑 apply_block_text：换块名 + 子条目原位替换 + 序列化生效；
- 本地化列：候选判定启发式 + 翻译器接入展示；
- 真实数据冒烟：游戏 MIO 组织文件 载入→序列化→重解析 层级一致。
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from structure_view import StructureView, is_loc_candidate  # noqa: E402
from tree_node import parse_pdx_text_to_nodes  # noqa: E402

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


class _FakeLoc:
    """测试替身：与 LocalizationManager 相同的 get_name 接口。"""

    def __init__(self, mapping):
        self._m = mapping

    def get_name(self, key):
        return self._m.get(key, "")


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


class StructureViewEditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = StructureView()
        self.view.load_text(SAMPLE)

    def _org_item(self):
        return _items(self.view)[0]

    def test_inline_key_rename(self):
        org = self._org_item()
        name_row = org.child(0)
        node = name_row.data(0, Qt.ItemDataRole.UserRole)
        self.assertTrue(self.view._commit_edit(name_row, node, StructureView.COL_KEY,
                                               "renamed_key"))
        self.assertEqual(node.key, "renamed_key")
        self.assertEqual(node.raw_lines, [])
        self.assertIn("renamed_key = GER_mio_name", self.view.to_pdx_text())

    def test_inline_key_rename_noop_on_same(self):
        org = self._org_item()
        name_row = org.child(0)
        node = name_row.data(0, Qt.ItemDataRole.UserRole)
        self.assertFalse(self.view._commit_edit(
            name_row, node, StructureView.COL_KEY, "name"))

    def test_inline_value_edit(self):
        org = self._org_item()
        name_row = org.child(0)
        node = name_row.data(0, Qt.ItemDataRole.UserRole)
        self.assertTrue(self.view._commit_edit(name_row, node, StructureView.COL_VALUE,
                                               "new_value_here"))
        self.assertEqual(node.value, "new_value_here")
        self.assertIn("name = new_value_here", self.view.to_pdx_text())

    def test_statement_edit_updates_raw_lines(self):
        org = self._org_item()
        stmt = org.child(5).child(0)
        node = stmt.data(0, Qt.ItemDataRole.UserRole)
        new_stmt = "num_of_military_factories > 10"
        self.assertTrue(self.view._commit_edit(stmt, node, StructureView.COL_VALUE,
                                               new_stmt))
        self.assertEqual(node.raw_lines, [new_stmt])
        self.assertIn(new_stmt, self.view.to_pdx_text())

    def test_block_edit_rename_and_children(self):
        org = self._org_item()
        equip = org.child(2)
        new_text = "equipment_new = {\n\t\ttype = other_type\n\t\textra = yes\n\t}"
        self.assertTrue(self.view.apply_block_text(equip, new_text))
        node = equip.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(node.key, "equipment_new")
        self.assertEqual([c.key for c in node.children], ["type", "extra"])
        # 视图行同步：摘要数量与子行刷新
        self.assertEqual(equip.text(1), "{ … } · 2 项")
        self.assertEqual(equip.childCount(), 2)
        self.assertEqual(equip.child(1).text(0), "extra")
        out = self.view.to_pdx_text()
        self.assertIn("equipment_new = {", out)
        self.assertIn("extra = yes", out)
        self.assertNotIn("\tequipment = {", out)

    def test_block_edit_invalid_text_rejected(self):
        org = self._org_item()
        equip = org.child(2)
        with self.assertRaises(ValueError):
            self.view.apply_block_text(equip, "not a block = just value")

    def test_structure_changed_signal(self):
        org = self._org_item()
        name_row = org.child(0)
        node = name_row.data(0, Qt.ItemDataRole.UserRole)
        fired = []
        self.view.structureChanged.connect(lambda: fired.append(1))
        self.view._loading = False
        self.view._on_item_changed(name_row, StructureView.COL_KEY)  # 同文本 → 不触发
        self.assertEqual(fired, [])
        name_row.setText(StructureView.COL_KEY, "renamed_key")
        self.view._on_item_changed(name_row, StructureView.COL_KEY)
        self.assertEqual(len(fired), 1)


class StructureViewLocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_loc_candidate_heuristic(self):
        self.assertTrue(is_loc_candidate("GER_mio_name"))
        self.assertTrue(is_loc_candidate("my_trait_loc"))
        self.assertFalse(is_loc_candidate(""))
        self.assertFalse(is_loc_candidate("1.5"))
        self.assertFalse(is_loc_candidate("1939.1.1"))
        self.assertFalse(is_loc_candidate("@var"))
        self.assertFalse(is_loc_candidate("yes"))
        # 纯字母仍像键（如 has_dlc），交给翻译器查，查不到第三列留空
        self.assertTrue(is_loc_candidate("has_dlc"))

    def test_loc_column_filled_from_translator(self):
        view = StructureView(localization=_FakeLoc({
            "GER_mio_name": "德国军用工业组织",
            "my_trait_loc": "我的特质",
        }))
        view.load_text(SAMPLE)
        org = _items(view)[0]
        self.assertEqual(org.child(0).text(2), "德国军用工业组织")
        self.assertEqual(org.child(3).child(1).text(2), "我的特质")  # trait.name
        # 数字值无翻译
        self.assertEqual(org.child(2).child(1).text(2), "")  # cost = 1.5

    def test_refresh_localization_after_swap(self):
        view = StructureView(localization=None)
        view.load_text(SAMPLE)
        org = _items(view)[0]
        self.assertEqual(org.child(0).text(2), "")
        view.set_localization(_FakeLoc({"GER_mio_name": "德国组织"}))
        self.assertEqual(org.child(0).text(2), "德国组织")
        # tooltip 给出所查键
        self.assertIn("GER_mio_name", org.child(0).toolTip(2))


class StructureViewRealDataTest(unittest.TestCase):
    """真实数据冒烟：游戏 MIO 组织文件 载入→序列化→重解析 层级一致。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _walk_count(self, item):
        n = 1
        for j in range(item.childCount()):
            n += self._walk_count(item.child(j))
        return n

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

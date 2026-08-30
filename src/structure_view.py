"""结构体展示组件（StructureView）——PDX 块的列表式结构浏览与双击编辑。

交互约定（按用户拍板）：
- 块展示为列表：每个块是一行，块内条目作为子行，用树形缩进表达嵌套；
- 组件默认全部展开（载入/重建后 expandAll）；
- 双击块字段（键列）→ 就地修改块名；
- 双击块行值列（`{ … }` 摘要）→ 展开/收起该块；
- 双击值条目键列/值列 → 就地改名/改值；
- 不展示原始文本结构（无整块文本编辑器）；
- 本地化展示：接入 LocalizationManager 翻译器，把"像本地化键"的值/裸 token
  的中文翻译显示在第三列，悬停 tooltip 给出所查键名，双击复制翻译。

数据底座是 tree_node.TreeNode（全保真：顺序、重复键、比较语句、原始行），
所有编辑直接写回 TreeNode，`to_pdx_text()` 可随时导出序列化文本。
注意：就地编辑键/值会清除该节点的 raw_lines（否则原始行会覆盖编辑结果）。
"""

from __future__ import annotations

import os
import re
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QTreeWidget,
    QTreeWidgetItem,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theme import COLORS  # noqa: E402
from tree_node import COMPARE_OPERATORS, TreeNode, parse_pdx_text_to_nodes  # noqa: E402

# 纯数字/日期/坐标类 token：不可能是本地化键
_NUM_TOKEN_RE = re.compile(r"^[\d\.\-+\s:]+$")


def is_loc_candidate(token):
    """判断一个 token 是否"像本地化键"（值得送去翻译器查一次）。

    规则（启发式）：非空、非纯数字/日期、含 ASCII 字母、无空格、
    不含比较运算符、不是 @ 变量、不是 yes/no，长度不超过 120。
    """
    if not token:
        return False
    t = str(token).strip().strip('"')
    if not t or _NUM_TOKEN_RE.match(t):
        return False
    if t.startswith("@") or t.lower() in ("yes", "no"):
        return False
    if not re.search(r"[A-Za-z]", t):
        return False
    if " " in t:
        return False
    if any(op in t for op in COMPARE_OPERATORS):
        return False
    return len(t) <= 120


class StructureView(QTreeWidget):
    """PDX 结构体列表树：默认展开，双击块字段改名/双击块行展开收起，第三列本地化。"""

    structureChanged = pyqtSignal()  # 任何成功写回后触发

    COL_KEY, COL_VALUE, COL_LOC = 0, 1, 2

    def __init__(self, parent=None, localization=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHeaderLabels(["键", "值", "本地化"])
        self._root = TreeNode("block", "(root)")   # 逻辑根：children 为顶层条目
        self._loc = localization
        self._loading = False
        self._build_ui()
        self.itemDoubleClicked.connect(self._on_double_clicked)
        self.itemChanged.connect(self._on_item_changed)

    # ---------- UI ----------

    def _build_ui(self):
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setExpandsOnDoubleClick(False)  # 展开收起由块行值列双击手动接管
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(False)
        header = self.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.setColumnWidth(self.COL_KEY, 300)
        self.setColumnWidth(self.COL_VALUE, 280)
        self.setColumnWidth(self.COL_LOC, 240)

    # ---------- 数据装载 ----------

    def set_localization(self, mgr):
        """接入/更换翻译器（LocalizationManager 或任何带 get_name 的对象）。"""
        self._loc = mgr
        self.refresh_localization()

    def load_text(self, text):
        """解析 PDX 文本并渲染。"""
        self.load_nodes(parse_pdx_text_to_nodes(text or ""))

    def load_nodes(self, nodes):
        """用 TreeNode 列表作为顶层条目渲染。"""
        self._root = TreeNode("block", "(root)")
        for n in nodes or []:
            self._root.add_child(n)
        self.rebuild()

    def root_node(self):
        return self._root

    def to_pdx_text(self):
        """把当前结构序列化回 PDX 文本（每个顶层条目一段）。"""
        return "\n".join(c.to_pdx(indent=0) for c in self._root.children)

    def rebuild(self):
        """从 TreeNode 全量重建视图；默认全部展开。"""
        self._loading = True
        try:
            self.clear()
            for node in self._root.children:
                item = self._make_item(node)
                self.addTopLevelItem(item)
                self._fill_children(item, node)
                self._decorate(item, node)
            self.expandAll()
        finally:
            self._loading = False

    # ---------- 渲染 ----------

    def _make_item(self, node):
        item = QTreeWidgetItem()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        item.setData(0, Qt.ItemDataRole.UserRole, node)
        return item

    def _fill_children(self, item, node):
        if node.node_type != "block":
            return
        for child in node.children:
            sub = self._make_item(child)
            item.addChild(sub)
            self._fill_children(sub, child)
            self._decorate(sub, child)

    def _decorate(self, item, node):
        """写入三列文本与配色/tooltip（不改 TreeNode）。"""
        is_block = node.node_type == "block"
        is_stmt = (not node.key) and bool(node.raw_lines)  # 比较语句节点
        # 列0：键
        if is_stmt:
            key_text = "·"
        elif is_block:
            key_text = node.key or "（未命名块）"
        else:
            key_text = node.key
        item.setText(self.COL_KEY, key_text)
        # 列1：值 / 块摘要
        if is_block:
            item.setText(self.COL_VALUE, "{ … } · %d 项" % len(node.children))
        else:
            item.setText(self.COL_VALUE, node.value if node.value else "")
        # 配色
        accent = QBrush(QColor(COLORS["accent"]))
        secondary = QBrush(QColor(COLORS["text_secondary"]))
        if is_block:
            font = item.font(self.COL_KEY)
            font.setBold(True)
            item.setFont(self.COL_KEY, font)
            item.setForeground(self.COL_KEY, accent)
            item.setForeground(self.COL_VALUE, secondary)
        elif is_stmt:
            item.setForeground(self.COL_KEY, secondary)
            item.setForeground(self.COL_VALUE, accent)
        item.setForeground(self.COL_LOC, secondary)
        # tooltip
        if is_block:
            item.setToolTip(self.COL_KEY, "块字段：%s\n双击修改块名" % (node.key or "（未命名）"))
            item.setToolTip(self.COL_VALUE, "双击展开/收起")
        elif is_stmt:
            item.setToolTip(self.COL_VALUE, "比较语句：双击值列可整句编辑")
        if node.key and not is_block:
            item.setToolTip(self.COL_KEY, "键：%s\n双击改名" % node.key)
        self._apply_loc(item, node)

    def _apply_loc(self, item, node):
        """第三列：翻译器查询（值优先，裸 token 用键），写文本与 tooltip。"""
        if node.node_type == "block":
            item.setText(self.COL_LOC, "")
            item.setToolTip(self.COL_LOC, "")
            return
        is_stmt = (not node.key) and bool(node.raw_lines)
        value = node.value if node.value else ""
        token = value if value else ("" if is_stmt else node.key)
        if not is_loc_candidate(token):
            item.setText(self.COL_LOC, "")
            item.setToolTip(self.COL_LOC, "")
            return
        trans = self._lookup(token)
        item.setText(self.COL_LOC, trans)
        if trans:
            item.setToolTip(
                self.COL_LOC, "本地化键：%s\n翻译：%s\n（双击复制翻译）" % (token, trans))
        else:
            item.setToolTip(self.COL_LOC, "本地化键：%s\n（翻译器无此键）" % token)

    def _lookup(self, token):
        try:
            return (self._loc.get_name(token) or "").strip() if self._loc else ""
        except Exception:
            return ""

    def refresh_localization(self):
        """全量刷新第三列。"""
        self._loading = True
        try:
            for i in range(self.topLevelItemCount()):
                self._refresh_item_loc(self.topLevelItem(i))
        finally:
            self._loading = False

    def _refresh_item_loc(self, item):
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node is not None:
            self._apply_loc(item, node)
        for j in range(item.childCount()):
            self._refresh_item_loc(item.child(j))

    # ---------- 交互 ----------

    def _on_double_clicked(self, item, col):
        if self._loading:
            return
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node is None:
            return
        is_stmt = (not node.key) and bool(node.raw_lines)
        if col == self.COL_KEY:
            if is_stmt:
                return  # 语句节点无键名
            self.editItem(item, col)
        elif col == self.COL_VALUE:
            if node.node_type == "block":
                item.setExpanded(not item.isExpanded())  # 块行：展开/收起
            else:
                self.editItem(item, col)
        elif col == self.COL_LOC:
            trans = item.text(self.COL_LOC)
            if trans:
                QApplication.clipboard().setText(trans)

    def _on_item_changed(self, item, col):
        """行内编辑落盘：写回 TreeNode 并刷新展示。"""
        if self._loading:
            return
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node is None:
            return
        if self._commit_edit(item, node, col, item.text(col)):
            self._loading = True
            try:
                self._decorate(item, node)
            finally:
                self._loading = False
            self.structureChanged.emit()

    def _commit_edit(self, item, node, col, text):
        """把行内编辑结果写回节点；成功返回 True。测试可直接调用。"""
        text = (text or "").strip()
        if col == self.COL_KEY:
            if (not node.key) and node.raw_lines:
                return False  # 比较语句节点没有键名，键列不可写
            if node.node_type == "block":
                if not text or text == "（未命名块）":
                    return False
            elif not node.raw_lines and text == node.key:
                return False
            node.key = text
            node.raw_lines = []
            if node.parent is not None and node.parent.raw_lines:
                node.parent.raw_lines = []
            return True
        if col == self.COL_VALUE and node.node_type != "block":
            is_stmt = (not node.key) and bool(node.raw_lines)
            if is_stmt:
                if text == node.value:
                    return False
                node.value = text
                node.raw_lines = [text]
            else:
                if text == node.value:
                    return False
                node.value = text
                node.raw_lines = []
            if node.parent is not None and node.parent.raw_lines:
                node.parent.raw_lines = []  # 结构已变，父块原始行作废
            return True
        return False

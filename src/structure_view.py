"""结构体展示组件（StructureView）——PDX 块的列表式结构浏览与双击编辑。

交互约定（按用户拍板）：
- 块展示为列表：每个块是一行，块内条目作为子行，用树形缩进表达嵌套；
- 组件默认全部展开（载入/重建后 expandAll）；
- 双击块字段（键列）→ 就地修改块名；
- 双击块行值列（`{ … }` 摘要）→ 展开/收起该块；
- 双击值条目键列/值列 → 就地改名/改值；
- 不展示原始文本结构（无整块文本编辑器）；
- 本地化与树形编辑器（generic_tree_editor）同款样式：GuiTranslator.translate_node
  提供 `键--中文` / `值--中文值` 内联翻译，块/键/值全部生效；显示与编辑分离
  （编辑器里永远是原始英文键值，展示层才带中文后缀）；
- 右键块行/空白处复刻树形编辑器的添加功能：NodeEditDialog（词条/模板搜索）
  添加节点，接受后原位插入并展开。

数据底座是 tree_node.TreeNode（全保真：顺序、重复键、比较语句、原始行），
所有编辑直接写回 TreeNode，`to_pdx_text()` 可随时导出序列化文本。
注意：就地编辑键/值会清除该节点的 raw_lines（否则原始行会覆盖编辑结果）。
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import (
    QEvent,
    QModelIndex,
    QRect,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QBrush, QColor, QFontMetrics, QTextCursor, QTextOption
from PyQt6.QtWidgets import (
    QAbstractItemDelegate,
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QMenu,
    QPlainTextEdit,
    QStyledItemDelegate,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theme import COLORS  # noqa: E402
from tree_node import TreeNode, parse_pdx_text_to_nodes  # noqa: E402


class StructureItem(QTreeWidgetItem):
    """结构条目：DisplayRole 展示层带 `--中文`，EditRole 恒为原始键/值。"""

    def __init__(self, view, node):
        super().__init__()
        self.view = view
        self.node = node
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)

    # ---------- 角色分离 ----------

    def data(self, column, role):
        node = self.node
        if node is not None and role == Qt.ItemDataRole.DisplayRole:
            return self.view.display_text(node, column)
        if node is not None and role == Qt.ItemDataRole.EditRole:
            is_stmt = (not node.key) and bool(node.raw_lines)
            if column == StructureView.COL_KEY:
                return None if is_stmt else node.key
            if column == StructureView.COL_VALUE and node.node_type != "block":
                return node.value
            return None
        return super().data(column, role)

    def setData(self, column, role, value):
        """编辑器提交：走统一写回（不落展示文本，展示层由 DisplayRole 现算）。

        注意：QTreeWidgetItem.setData 的 C++ 签名返回 void，重写必须返回
        None——返回 bool 会让 PyQt6 在提交瞬间抛 invalid result 并直接崩溃
        （"退出编辑即崩"的根因）。
        defer=True：此时正处于模型 setData 调用栈内，行刷新与信号必须延迟到
        事件循环，避免 dataChanged 重入。
        """
        if role == Qt.ItemDataRole.EditRole and self.node is not None:
            text = "" if value is None else str(value)
            self.view._commit_node_edit(self.node, column, text, defer=True)
            return None
        return super().setData(column, role, value)


class StructureEditDelegate(QStyledItemDelegate):
    """行内编辑委托：加高的多行编辑框，长键/长值换行完整可见。

    Enter 提交、Shift+Enter 换行、Esc 取消、失焦提交（与树形编辑器一致）。
    """

    EXTRA_LINES = 3  # 编辑框在行高基础上向下扩展的行数

    def createEditor(self, parent, option, index):
        editor = QPlainTextEdit(parent)
        editor.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor.installEventFilter(self)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        """编辑框在单元格基础上加高 EXTRA_LINES 行（向上扩展，贴住视口顶）。"""
        rect = QRect(option.rect)
        fm = QFontMetrics(editor.font())
        extra = fm.height() * self.EXTRA_LINES
        top = max(0, rect.top() - extra)
        height = rect.bottom() - top + 1
        editor.setGeometry(QRect(rect.left(), top, rect.width(), height))

    def setEditorData(self, editor, index):
        if isinstance(editor, QPlainTextEdit):
            editor.setPlainText(index.data(Qt.ItemDataRole.EditRole) or "")
            editor.moveCursor(QTextCursor.MoveOperation.End)
            return
        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QPlainTextEdit):
            model.setData(index, editor.toPlainText(), Qt.ItemDataRole.EditRole)
            return
        super().setModelData(editor, model, index)

    def eventFilter(self, obj, event):
        if isinstance(obj, QPlainTextEdit):
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
                        event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self.commitData.emit(obj)
                    self.closeEditor.emit(
                        obj, QAbstractItemDelegate.EndEditHint.SubmitModelCache)
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self.closeEditor.emit(
                        obj, QAbstractItemDelegate.EndEditHint.RevertModelCache)
                    return True
            elif event.type() == QEvent.Type.FocusOut:
                # 失焦提交，确保修改被保存而不是被丢弃（编辑器已销毁则忽略）
                try:
                    self.commitData.emit(obj)
                except RuntimeError:
                    pass
        return super().eventFilter(obj, event)


class StructureView(QTreeWidget):
    """PDX 结构体列表树：默认展开，双击块字段改名/双击块行展开收起，
    键值内联本地化（树形编辑器样式），右键添加节点（词条/模板）。"""

    structureChanged = pyqtSignal()  # 任何成功写回/添加后触发

    COL_KEY, COL_VALUE = 0, 1

    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(["键", "值"])
        self._root = TreeNode("block", "(root)")   # 逻辑根：children 为顶层条目
        self.translator = translator               # GuiTranslator 或同接口替身
        self._loading = False
        self._build_ui()
        self.itemDoubleClicked.connect(self._on_double_clicked)
        self.customContextMenuRequested.connect(self._show_menu)

    # ---------- UI ----------

    def _build_ui(self):
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setExpandsOnDoubleClick(False)  # 展开收起由块行值列双击手动接管
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setItemDelegate(StructureEditDelegate(self))  # 加高多行编辑框
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(False)
        header = self.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.setColumnWidth(self.COL_KEY, 380)
        self.setColumnWidth(self.COL_VALUE, 320)

    # ---------- 数据装载 ----------

    def set_translator(self, translator):
        """接入/更换翻译器（GuiTranslator 或任何带 translate_node 的对象）。"""
        self.translator = translator
        self.refresh_localization()

    # 兼容旧名
    set_localization = set_translator

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
                item = StructureItem(self, node)
                self.addTopLevelItem(item)
                self._fill_children(item, node)
                self._decorate(item, node)
            self.expandAll()
        finally:
            self._loading = False

    # ---------- 渲染 ----------

    def display_text(self, node, column):
        """展示层文本：树形编辑器样式 `键--中文` / `值--中文值`（翻译不同才加后缀）。"""
        cn_key, cn_val = self._translate_node(node)
        if column == self.COL_KEY:
            if node.node_type == "block":
                base = node.key or "（未命名块）"
            elif (not node.key) and node.raw_lines:
                return "·"  # 比较语句无键名
            else:
                base = node.key
            if cn_key and cn_key != base:
                return "%s--%s" % (base, cn_key)
            return base
        # 值列
        if node.node_type == "block":
            return "{ … } · %d 项" % len(node.children)
        v = node.value or ""
        if cn_val and cn_val != v:
            return "%s--%s" % (v, cn_val) if v else cn_val
        return v

    def _translate_node(self, node):
        """经翻译器取 (中文键, 中文值)；无翻译器/无翻译时返回原始文本。"""
        if self.translator is None:
            return node.key, node.value or ""
        try:
            cn_key, cn_val = self.translator.translate_node(
                node.key, node.value if node.value else None)
        except Exception:
            return node.key, node.value or ""
        cn_key = cn_key or node.key
        cn_val = cn_val if cn_val is not None else (node.value or "")
        return cn_key, cn_val

    def _fill_children(self, item, node):
        if node.node_type != "block":
            return
        for child in node.children:
            sub = StructureItem(self, child)
            item.addChild(sub)
            self._fill_children(sub, child)
            self._decorate(sub, child)

    def _decorate(self, item, node):
        """写入配色/tooltip（文本由 DisplayRole 现算，这里不落文本）。"""
        is_block = node.node_type == "block"
        is_stmt = (not node.key) and bool(node.raw_lines)
        accent = QBrush(QColor(COLORS["accent"]))
        secondary = QBrush(QColor(COLORS["text_secondary"]))
        if is_block:
            font = item.font(self.COL_KEY)
            font.setBold(True)
            item.setFont(self.COL_KEY, font)
            item.setForeground(self.COL_KEY, accent)
            item.setForeground(self.COL_VALUE, secondary)
            cn_key, _ = self._translate_node(node)
            tip = "块字段：%s" % (node.key or "（未命名）")
            if cn_key and cn_key != (node.key or ""):
                tip += "\n中文：%s" % cn_key
            tip += "\n子条目 %d 项\n双击键列改块名，双击值列展开/收起" % len(node.children)
            item.setToolTip(self.COL_KEY, tip)
            item.setToolTip(self.COL_VALUE, "双击展开/收起")
        elif is_stmt:
            item.setForeground(self.COL_KEY, secondary)
            item.setForeground(self.COL_VALUE, accent)
            item.setToolTip(self.COL_VALUE,
                            "比较语句：%s\n双击值列可整句编辑" % (node.value or ""))
        else:
            cn_key, cn_val = self._translate_node(node)
            tip = "键：%s" % node.key
            if cn_key and cn_key != node.key:
                tip += "\n中文：%s" % cn_key
            tip += "\n值：%s" % (node.value or "")
            if cn_val and cn_val != (node.value or ""):
                tip += "\n中文：%s" % cn_val
            tip += "\n双击键列改名，双击值列改值"
            item.setToolTip(self.COL_KEY, tip)
            item.setToolTip(self.COL_VALUE, "双击改值")

    def refresh_localization(self):
        """翻译器变化后全量重绘展示层。"""
        self._loading = True
        try:
            for i in range(self.topLevelItemCount()):
                self._refresh_item(self.topLevelItem(i))
        finally:
            self._loading = False

    def _refresh_item(self, item):
        node = item.node
        if node is not None:
            self._decorate(item, node)
            item.emitDataChanged()
        for j in range(item.childCount()):
            self._refresh_item(item.child(j))

    # ---------- 交互 ----------

    def _on_double_clicked(self, item, col):
        if self._loading:
            return
        node = getattr(item, "node", None)
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

    # ---------- 写回 ----------

    def _commit_node_edit(self, node, col, text, defer=False):
        """行内编辑统一写回；成功返回 True 并触发 structureChanged。

        defer=True 时（编辑器提交栈内）行刷新与信号延迟到事件循环执行，
        避免 dataChanged 重入导致崩溃。
        """
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
        elif col == self.COL_VALUE and node.node_type != "block":
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
        else:
            return False
        if node.parent is not None and node.parent.raw_lines:
            node.parent.raw_lines = []  # 结构已变，父块原始行作废
        if defer:
            QTimer.singleShot(0, lambda: self._resync_row(node))
            QTimer.singleShot(0, self.structureChanged.emit)
        else:
            self._resync_row(node)
            self.structureChanged.emit()
        return True

    def _resync_row(self, node):
        """写回后刷新对应行（含父块摘要数量）。"""
        try:
            item = self._find_item(node)
            if item is not None:
                item.emitDataChanged()
            parent = node.parent
            if parent is not None and parent is not self._root:
                pitem = self._find_item(parent)
                if pitem is not None:
                    pitem.emitDataChanged()
        except RuntimeError:
            pass  # 视图/条目已销毁（窗口关闭等），无需刷新

    def _find_item(self, node):
        """在当前视图中按节点身份查找条目。"""
        def walk(item):
            try:
                if item.node is node:
                    return item
                for j in range(item.childCount()):
                    got = walk(item.child(j))
                    if got is not None:
                        return got
            except RuntimeError:
                return None  # 条目已被销毁
            return None
        for i in range(self.topLevelItemCount()):
            got = walk(self.topLevelItem(i))
            if got is not None:
                return got
        return None

    # ---------- 添加（复刻树形编辑器） ----------

    def _show_menu(self, pos):
        """右键菜单：块行/空白处提供 添加节点（词条/模板）——与树形编辑器一致。"""
        item = self.itemAt(pos)
        target = None
        if item is not None:
            node = getattr(item, "node", None)
            if node is None or node.node_type != "block":
                return  # 值行/语句行不提供添加入口
            target = item  # 块行 → 添加为该块子条目
        # item 为 None（空白处）→ 添加为顶层条目
        menu = QMenu(self)
        act_add = menu.addAction("🔍 添加节点（词条/模板）...")
        act_add.triggered.connect(lambda: self._open_add_dialog(target))
        menu.exec(self.viewport().mapToGlobal(pos))

    def _open_add_dialog(self, parent_item):
        """添加节点：NodeEditDialog（词条/模板搜索），接受后原位插入。"""
        from node_edit_dialog import NodeEditDialog
        dlg = NodeEditDialog(self.translator, parent=self)
        dlg.setWindowTitle("添加节点")

        def on_add_ok():
            new_node = dlg.get_node()
            if new_node is not None:
                self.add_node(new_node, parent_item)
            dlg.deleteLater()

        dlg.accepted.connect(on_add_ok)
        dlg.show()

    def add_node(self, new_node, parent_item=None):
        """插入节点：parent_item 为 None 时添加为顶层条目，否则作为该块子条目。"""
        if not isinstance(new_node, TreeNode):
            return None
        if parent_item is None:
            self._root.add_child(new_node)
            item = StructureItem(self, new_node)
            self.addTopLevelItem(item)
        else:
            parent_node = getattr(parent_item, "node", None)
            if parent_node is None or parent_node.node_type != "block":
                return None
            parent_node.add_child(new_node)
            item = StructureItem(self, new_node)
            parent_item.addChild(item)
            parent_item.setExpanded(True)
            parent_item.emitDataChanged()  # 摘要数量刷新
        self._fill_children(item, new_node)
        self._decorate(item, new_node)
        self.structureChanged.emit()
        return item

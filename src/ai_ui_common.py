"""AI 专用编辑器公共 UI 组件。

统一实现：
- EntityListSidebar：固定宽度侧边栏（实体列表 + 搜索 + CRUD 按钮），禁止横向滚动。
- KeyValueTableEditor：键值表编辑器（用于 research / required_taskforces 等映射）。
- ScriptBlockEditorDialog：高级脚本块编辑器（非树形页面，复用 NodeEditDialog /
  TemplateDialog / CustomStatementDialog / TermDialog 等现有能力）。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPushButton, QStyledItemDelegate,
    QTabWidget, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout,
    QWidget,
)


SIDEBAR_WIDTH = 300


def file_tooltip(entity, mod_path="", hoi4_path=""):
    """从实体字典生成「来源文件」悬停提示；无 file/rel 信息返回 None。

    entity: 含 file（绝对路径）/ rel（相对游戏或 mod 根路径）字段的字典。
    """
    if not isinstance(entity, dict):
        return None
    rel = entity.get("rel") or ""
    fp = entity.get("file") or ""
    if not rel and not fp:
        return None
    origin = "未知"
    if fp:
        norm = os.path.normpath(fp)
        if mod_path and norm.startswith(os.path.normpath(mod_path)):
            origin = "mod"
        elif hoi4_path and norm.startswith(os.path.normpath(hoi4_path)):
            origin = "游戏"
        else:
            origin = "外部"
    lines = ["文件：%s" % (rel or fp), "来源：%s" % origin]
    if rel and fp:
        lines.append("路径：%s" % fp)
    return "\n".join(lines)


class _ElideDelegate(QStyledItemDelegate):
    """QListWidget 文本省略号 delegate：防止长文本把侧边栏撑出横向滚动条。"""

    def paint(self, painter, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        elided = painter.fontMetrics().elidedText(
            text, Qt.TextElideMode.ElideRight, option.rect.width() - 8)
        opt = option.__class__(option)
        opt.text = elided
        super().paint(painter, opt, index)
        if elided != text:
            # 完整文本通过 tooltip 展示，由 EntityListSidebar 统一设置。
            pass


class EntityListSidebar(QWidget):
    """固定宽度侧边栏：搜索 + 实体列表 + 新建/复制/重命名/删除。"""

    currentChanged = pyqtSignal(object)  # entity_id or None
    createRequested = pyqtSignal()
    duplicateRequested = pyqtSignal()
    renameRequested = pyqtSignal()
    deleteRequested = pyqtSignal()

    def __init__(self, title="实体", parent=None, width=SIDEBAR_WIDTH,
                 enable_crud=True, mod_path="", hoi4_path=""):
        super().__init__(parent)
        self._items = []  # [(entity_id, label)]
        self._mod_path = mod_path
        self._hoi4_path = hoi4_path
        self.setFixedWidth(width)
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        root.addWidget(title_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        root.addWidget(self.search_edit)

        self.list = QListWidget()
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setItemDelegate(_ElideDelegate(self.list))
        self.list.currentItemChanged.connect(self._on_current_changed)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self.list, 1)

        if enable_crud:
            btns = QHBoxLayout()
            btns.setSpacing(4)
            self.create_btn = QPushButton("＋ 新建")
            self.duplicate_btn = QPushButton("⧉ 复制")
            self.rename_btn = QPushButton("✎ 改名")
            self.delete_btn = QPushButton("🗑 删除")
            for b in (self.create_btn, self.duplicate_btn,
                      self.rename_btn, self.delete_btn):
                b.setMinimumWidth(0)
                btns.addWidget(b)
            self.create_btn.clicked.connect(self.createRequested.emit)
            self.duplicate_btn.clicked.connect(self.duplicateRequested.emit)
            self.rename_btn.clicked.connect(self.renameRequested.emit)
            self.delete_btn.clicked.connect(self.deleteRequested.emit)
            root.addLayout(btns)
        else:
            self.create_btn = None
            self.duplicate_btn = None
            self.rename_btn = None
            self.delete_btn = None

    # ---------- 数据 ----------

    def set_entities(self, entities, keep_selection=False, tooltips=None):
        """entities: [(entity_id, label) 或 (entity_id, label, tooltip), ...]

        tooltips: 可选，按位置覆盖第三元素；条目缺省时回退为 label。
        """
        self._items = []
        for i, ent in enumerate(entities):
            eid, label = ent[0], ent[1]
            tip = None
            if tooltips is not None and i < len(tooltips):
                tip = tooltips[i]
            elif len(ent) > 2:
                tip = ent[2]
            self._items.append((eid, label, tip if tip else label))
        current = self.current_id()
        self.list.blockSignals(True)
        self.list.clear()
        for eid, label, tip in self._items:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, eid)
            item.setToolTip(tip)
            self.list.addItem(item)
        self.list.blockSignals(False)
        if keep_selection and current is not None:
            self.set_current(current)
        elif self.list.count() > 0:
            self.list.setCurrentRow(0)

    def set_current(self, entity_id):
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == entity_id:
                self.list.setCurrentItem(item)
                return True
        return False

    def current_id(self):
        item = self.list.currentItem()
        if item is not None:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def selected_item_text(self):
        item = self.list.currentItem()
        return item.text() if item is not None else ""

    def set_paths(self, mod_path="", hoi4_path=""):
        """设置 mod/游戏路径，供右键快速本地化编辑使用。"""
        self._mod_path = mod_path or ""
        self._hoi4_path = hoi4_path or ""

    def _on_context_menu(self, pos):
        """列表项右键菜单：快速编辑本地化。"""
        item = self.list.itemAt(pos)
        if item is None:
            return
        entity_id = item.data(Qt.ItemDataRole.UserRole) or ""
        if not entity_id or not self._mod_path:
            return
        menu = QMenu(self.list)
        act = menu.addAction("✎ 快速编辑本地化（{}）…".format(entity_id))
        act.triggered.connect(lambda _=False: self._open_quick_loc(entity_id))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _open_quick_loc(self, entity_id):
        """弹出快速本地化编辑小窗口。"""
        from quick_localisation_edit import QuickLocalisationEditDialog
        dlg = QuickLocalisationEditDialog(
            key=entity_id,
            mod_path=self._mod_path,
            hoi4_path=self._hoi4_path,
            parent=self)
        dlg.show()

    def _apply_filter(self, text):
        text = (text or "").strip().lower()
        self.list.blockSignals(True)
        self.list.clear()
        for eid, label, tip in self._items:
            if text and text not in label.lower():
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, eid)
            item.setToolTip(tip)
            self.list.addItem(item)
        self.list.blockSignals(False)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)
        else:
            self.currentChanged.emit(None)

    def _on_current_changed(self, current, _previous):
        if current is None:
            self.currentChanged.emit(None)
        else:
            self.currentChanged.emit(current.data(Qt.ItemDataRole.UserRole))


class KeyValueTableEditor(QWidget):
    """两列键值表编辑器，支持增删改、上移/下移。"""

    def __init__(self, key_label="键", value_label="值", parent=None):
        super().__init__(parent)
        self.key_label = key_label
        self.value_label = value_label
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([key_label, value_label])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self.table, 1)

        btns = QHBoxLayout()
        add_btn = QPushButton("＋ 添加")
        del_btn = QPushButton("🗑 删除选中")
        up_btn = QPushButton("⬆")
        down_btn = QPushButton("⬇")
        add_btn.clicked.connect(self.add_row)
        del_btn.clicked.connect(self.delete_selected)
        up_btn.clicked.connect(self.move_up)
        down_btn.clicked.connect(self.move_down)
        for b in (add_btn, del_btn, up_btn, down_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        root.addLayout(btns)

    def set_data(self, data):
        """data: dict 或 [(key, value), ...]"""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        items = data.items() if isinstance(data, dict) else data
        for k, v in items:
            self.add_row(k, v)
        self.table.blockSignals(False)

    def data(self):
        out = {}
        for r in range(self.table.rowCount()):
            k_item = self.table.item(r, 0)
            v_item = self.table.item(r, 1)
            k = k_item.text().strip() if k_item else ""
            v = v_item.text().strip() if v_item else ""
            if k:
                out[k] = v
        return out

    def rows(self):
        out = []
        for r in range(self.table.rowCount()):
            k_item = self.table.item(r, 0)
            v_item = self.table.item(r, 1)
            out.append((k_item.text().strip() if k_item else "",
                        v_item.text().strip() if v_item else ""))
        return out

    def add_row(self, key="", value=""):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(str(key)))
        self.table.setItem(r, 1, QTableWidgetItem(str(value)))

    def delete_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def move_up(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            return
        r = rows[0]
        if r <= 0:
            return
        self.table.insertRow(r - 1)
        for c in range(2):
            item = self.table.takeItem(r + 1, c)
            self.table.setItem(r - 1, c, item)
        self.table.removeRow(r + 1)
        self.table.selectRow(r - 1)

    def move_down(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            return
        r = rows[-1]
        if r >= self.table.rowCount() - 1:
            return
        self.table.insertRow(r + 2)
        for c in range(2):
            item = self.table.takeItem(r, c)
            self.table.setItem(r + 2, c, item)
        self.table.removeRow(r)
        self.table.selectRow(r + 1)


class ScriptBlockEditorDialog(QDialog):
    """单个高级脚本块编辑器（非树形页面）。

    编辑一个 `key = { ... }` 块：
    - 显示当前块的直接子节点；
    - 支持添加/编辑/删除/上移/下移；
    - 双击块子节点进入下一层（面包屑导航）；
    - 复用 NodeEditDialog / TemplateDialog / CustomStatementDialog / TermDialog。
    """

    def __init__(self, block_text, block_key="", translator=None,
                 custom_statement_path="", parent=None, title="编辑高级脚本块"):
        super().__init__(parent)
        self.block_key = block_key or "block"
        self.translator = translator
        self.custom_statement_path = custom_statement_path
        self._nav_stack = []  # [(label, node)]
        self._root_block = self._parse_block(block_text)
        self._current_block = self._root_block
        self._scalar_nodes = []
        self.setWindowTitle(title)
        self.resize(720, 560)
        self.setMinimumSize(620, 460)
        self._build_ui()
        self._refresh()

    # ---------- 解析 ----------

    def _parse_block(self, block_text):
        from tree_node import tree_from_pdx_text, parse_pdx_block_to_tree
        text = (block_text or "").strip()
        if not text:
            return parse_pdx_block_to_tree("", key=self.block_key)
        try:
            root = tree_from_pdx_text(text)
            if (root.children and root.children[0].node_type == "block"
                    and root.children[0].key == self.block_key):
                return root.children[0]
        except Exception:
            pass
        return parse_pdx_block_to_tree(text, key=self.block_key)

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("⬅ 返回上级")
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self._go_back)
        nav.addWidget(self.back_btn)
        self.breadcrumb_label = QLabel("")
        nav.addWidget(self.breadcrumb_label, 1)
        root.addLayout(nav)

        self.tabs = QTabWidget()
        edit_tab = QWidget()
        edit_lay = QVBoxLayout(edit_tab)
        edit_lay.setContentsMargins(0, 0, 0, 0)
        edit_lay.setSpacing(6)

        self.kv_table = KeyValueTableEditor("键", "值", self)
        edit_lay.addWidget(QLabel("键值字段"))
        edit_lay.addWidget(self.kv_table, 1)

        edit_lay.addWidget(QLabel("子块（双击进入）"))
        self.list = QListWidget()
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemDoubleClicked.connect(self._on_double_click)
        edit_lay.addWidget(self.list, 1)

        btns = QHBoxLayout()
        btns.setSpacing(4)
        add_btn = QPushButton("➕ 添加节点（词条/模板）")
        edit_btn = QPushButton("✏ 编辑选中")
        del_btn = QPushButton("🗑 删除选中")
        up_btn = QPushButton("⬆")
        down_btn = QPushButton("⬇")
        tpl_btn = QPushButton("📄 从模板插入")
        self.advanced_btn = QToolButton()
        self.advanced_btn.setText("高级 ▾")
        self.advanced_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        advanced_menu = QMenu(self.advanced_btn)
        self.raw_action = advanced_menu.addAction("📝 原始 PDX（兜底）")
        self.raw_action.triggered.connect(self._edit_raw)
        self.advanced_btn.setMenu(advanced_menu)
        add_btn.clicked.connect(self._add_node)
        edit_btn.clicked.connect(self._edit_node)
        del_btn.clicked.connect(self._delete_node)
        up_btn.clicked.connect(self._move_up)
        down_btn.clicked.connect(self._move_down)
        tpl_btn.clicked.connect(self._insert_template)
        for b in (add_btn, edit_btn, del_btn, up_btn, down_btn,
                  tpl_btn, self.advanced_btn):
            btns.addWidget(b)
        edit_lay.addLayout(btns)
        self.tabs.addTab(edit_tab, "键值/子块")

        tree_tab = QWidget()
        tree_lay = QVBoxLayout(tree_tab)
        tree_lay.setContentsMargins(0, 0, 0, 0)
        from ui_widgets import BlockTreeList
        self.struct_tree = BlockTreeList()
        tree_lay.addWidget(self.struct_tree)
        self.tabs.addTab(tree_tab, "结构化树")
        root.addWidget(self.tabs, 1)

        tool_btns = QHBoxLayout()
        self.custom_btn = QPushButton("⚙ 管理自定义语句")
        self.term_btn = QPushButton("📖 管理词条")
        self.save_tpl_btn = QPushButton("💾 保存为模板")
        self.custom_btn.clicked.connect(self._manage_custom_statements)
        self.term_btn.clicked.connect(self._manage_terms)
        self.save_tpl_btn.clicked.connect(self._save_as_template)
        for b in (self.custom_btn, self.term_btn, self.save_tpl_btn):
            tool_btns.addWidget(b)
        tool_btns.addStretch(1)
        root.addLayout(tool_btns)

        footer = QHBoxLayout()
        self.status_label = QLabel("")
        footer.addWidget(self.status_label, 1)
        cancel_btn = QPushButton("取消")
        ok_btn = QPushButton("✓ 确定")
        cancel_btn.clicked.connect(self.reject)
        ok_btn.clicked.connect(self.accept)
        footer.addWidget(cancel_btn)
        footer.addWidget(ok_btn)
        root.addLayout(footer)

    def _refresh(self):
        self._scalar_nodes = [c for c in self._current_block.children
                              if c.node_type != "block"]
        scalar_rows = [(c.key, c.value) for c in self._scalar_nodes]
        self.kv_table.set_data(scalar_rows)

        self.list.blockSignals(True)
        self.list.clear()
        for child in self._current_block.children:
            if child.node_type == "block":
                text = "%s = { ... }" % child.key
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, child)
                item.setToolTip(text)
                self.list.addItem(item)
        self.list.blockSignals(False)

        # 结构化树视图（BlockTreeList 封装，展示当前层的直接节点）
        self.struct_tree.clear()
        for child in self._current_block.children:
            if child.node_type == "block":
                self.struct_tree.add_item(child.key + " = { ... }", "", "")
            else:
                self.struct_tree.add_item(child.key, str(child.value or ""), "")

        # 面包屑
        parts = [self.block_key] + [label for label, _node in self._nav_stack]
        self.breadcrumb_label.setText(" > ".join(parts))
        self.back_btn.setEnabled(bool(self._nav_stack))
        self.status_label.setText("键值字段 %d 项 / 子块 %d 个" % (
            len(self._scalar_nodes), len([c for c in self._current_block.children
                                          if c.node_type == "block"])))
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    # ---------- 表格同步 ----------

    def _commit_table_to_children(self):
        """把键值表当前内容写回当前块的标量子节点（保持已有的块位置）。"""
        if not hasattr(self, "kv_table") or self._current_block is None:
            return
        from tree_node import TreeNode
        rows = self.kv_table.rows()
        scalars = [c for c in self._current_block.children
                   if c.node_type != "block"]
        for i, (key, value) in enumerate(rows):
            if i < len(scalars):
                scalars[i].key = key
                scalars[i].value = value
                scalars[i].raw_lines = []
            else:
                node = TreeNode("value", key, value)
                if scalars:
                    pos = self._current_block.children.index(scalars[-1]) + 1
                else:
                    pos = 0
                self._current_block.add_child(node, pos)
                scalars.append(node)
        if len(rows) < len(scalars):
            for node in scalars[len(rows):]:
                self._current_block.remove_child(node)

    # ---------- 导航 ----------

    def _on_double_click(self, item):
        node = item.data(Qt.ItemDataRole.UserRole)
        if node is not None and node.node_type == "block":
            self._commit_table_to_children()
            self._nav_stack.append((node.key, self._current_block))
            self._current_block = node
            self._refresh()

    def _go_back(self):
        if self._nav_stack:
            self._commit_table_to_children()
            _label, parent = self._nav_stack.pop()
            self._current_block = parent
            self._refresh()

    # ---------- 节点操作 ----------

    def _selected_node(self):
        item = self.list.currentItem()
        if item is not None:
            return item.data(Qt.ItemDataRole.UserRole)
        rows = sorted({i.row() for i in self.kv_table.table.selectedIndexes()})
        if rows:
            r = rows[0]
            if 0 <= r < len(self._scalar_nodes):
                return self._scalar_nodes[r]
        return None

    def _add_node(self):
        from node_edit_dialog import NodeEditDialog
        dlg = NodeEditDialog(self.translator, parent=self)
        dlg.setWindowTitle("添加节点")

        def on_ok():
            node = dlg.get_node()
            if node is not None:
                self._current_block.add_child(node)
                self._refresh()
            dlg.deleteLater()

        dlg.accepted.connect(on_ok)
        dlg.show()

    def _edit_node(self):
        from node_edit_dialog import NodeEditDialog
        node = self._selected_node()
        if node is None:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return
        dlg = NodeEditDialog(self.translator, node=node, parent=self)
        dlg.setWindowTitle("编辑节点")

        def on_ok():
            result = dlg.get_node()
            if result is not None:
                idx = node.child_index()
                if idx >= 0:
                    node.parent.children[idx] = result
                    result.parent = node.parent
                    node.parent = None
                    self._refresh()
            dlg.deleteLater()

        dlg.accepted.connect(on_ok)
        dlg.show()

    def _delete_node(self):
        node = self._selected_node()
        if node is None:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除节点 '%s' 吗？" % node.key)
        if reply == QMessageBox.StandardButton.Yes:
            self._current_block.remove_child(node)
            self._refresh()

    def _move_up(self):
        node = self._selected_node()
        if node is not None and node.child_index() > 0:
            node.move_up()
            self._refresh()

    def _move_down(self):
        node = self._selected_node()
        if node is not None and node.parent and \
                node.child_index() < len(node.parent.children) - 1:
            node.move_down()
            self._refresh()

    def _insert_template(self):
        from template_dialog import TemplateDialog
        dlg = TemplateDialog(parent=self)

        def on_ok():
            node = dlg.get_node()
            if node is not None:
                self._current_block.add_child(node)
                self._refresh()
            dlg.deleteLater()

        dlg.accepted.connect(on_ok)
        dlg.show()

    def _edit_raw(self):
        from PyQt6.QtWidgets import QTextEdit
        self._commit_table_to_children()
        dlg = QDialog(self)
        dlg.setWindowTitle("原始 PDX 文本")
        dlg.setMinimumSize(480, 360)
        lay = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setPlainText(self._current_block.to_pdx())
        lay.addWidget(te)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("取消")
        ok = QPushButton("应用")
        cancel.clicked.connect(dlg.reject)
        ok.clicked.connect(dlg.accept)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

        def on_ok():
            from tree_node import parse_pdx_block_to_tree
            text = te.toPlainText().strip()
            if text:
                new_block = parse_pdx_block_to_tree(text, key=self._current_block.key)
                self._current_block.key = new_block.key
                self._current_block.node_type = new_block.node_type
                self._current_block.value = new_block.value
                self._current_block.children = new_block.children
                for c in self._current_block.children:
                    c.parent = self._current_block
                self._current_block.raw_lines = []
                self._refresh()
            dlg.deleteLater()

        dlg.accepted.connect(on_ok)
        dlg.show()

    # ---------- 工具 ----------

    def result_block_text(self):
        """返回当前编辑块的 PDX 文本（供调用方读取结果）。"""
        self._commit_table_to_children()
        return self._current_block.to_pdx()

    def _manage_custom_statements(self):
        from custom_statement_dialog import CustomStatementDialog
        dlg = CustomStatementDialog(
            self.translator, self.custom_statement_path, parent=self)
        dlg.show()

    def _manage_terms(self):
        from term_dialog import TermDialog
        from term_registry import get_term_registry
        dlg = TermDialog(get_term_registry(), parent=self)
        dlg.show()

    def _save_as_template(self):
        from PyQt6.QtWidgets import QInputDialog
        from template_scheduler import get_template_scheduler
        from write_utils import atomic_write_text
        import os
        name, ok = QInputDialog.getText(
            self, "保存为模板", "模板名称:", text=self._current_block.key)
        if not ok or not (name or "").strip():
            return
        self._commit_table_to_children()
        content = self._current_block.to_pdx()
        scheduler = get_template_scheduler()
        ttype = "custom"
        existing = None
        for t in scheduler.search_templates(template_type=ttype, include_system=False):
            if t["name"] == name.strip():
                existing = t["filepath"]
                break
        if existing:
            try:
                os.makedirs(os.path.dirname(existing), exist_ok=True)
                atomic_write_text(existing, content)
            except Exception as e:
                QMessageBox.critical(self, "错误", "保存模板失败：%s" % e)
                return
            QMessageBox.information(self, "成功", "模板已更新：\n%s" % existing)
            return
        path = scheduler.create_template(name.strip(), content, ttype)
        if path:
            QMessageBox.information(self, "成功", "模板已保存：\n%s" % path)
        else:
            QMessageBox.warning(self, "错误", "保存模板失败")

    # ---------- 结果 ----------

    def get_block_text(self):
        self._commit_table_to_children()
        return self._root_block.to_pdx()

    def get_block_node(self):
        return self._root_block

"""模板管理对话框模块

提供 TemplateManagerDialog：
- 左侧：模板文件列表（支持搜索）
- 右侧：树形编辑器（基于 TreeNode + FocusTreeModel）编辑模板内容
- 模板操作：新建/删除/保存模板（保存到当前选中的模板文件）
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTreeView,
    QMessageBox, QInputDialog, QSplitter, QWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

from tree_node import TreeNode, parse_pdx_text_to_nodes
from tree_model import FocusTreeModel
from template_scheduler import get_template_scheduler, TEMPLATE_TYPES


class TemplateManagerDialog(QDialog):
    """模板管理对话框 - 非模态

    左侧：模板文件列表（按类型目录组织，支持关键词搜索）
    右侧：树形编辑器（编辑模板内容）+ 节点操作 + 变量设置

    变量功能：
    - 模板内容中的 __变量名__ 占位符会被识别为模板变量
    - "变量设置"对话框可为每个变量填写中文说明并勾选是否启用（使用时填入）
    """

    templates_changed = pyqtSignal()

    def __init__(self, scheduler=None, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler or get_template_scheduler()
        self.current_filepath = None

        self.setWindowTitle("模板管理")
        self.setMinimumSize(900, 580)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._load_template_list()

    # ────────────── UI ──────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 左侧：搜索 + 模板列表 ──
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("模板名 / 变量名…")
        self.search_edit.textChanged.connect(self._load_template_list)
        search_row.addWidget(self.search_edit)
        left.addLayout(search_row)
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        left.addWidget(self.template_list)
        left_widget = QWidget()
        left_widget.setLayout(left)

        # ── 右侧：树形编辑 ──
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)

        # 模板信息行
        info_row = QHBoxLayout()
        self.name_label = QLabel("未选择模板")
        info_row.addWidget(self.name_label)
        info_row.addStretch()
        right.addLayout(info_row)

        # 节点操作按钮
        node_btn_row = QHBoxLayout()
        for text, slot in [
            ("+ 添加节点", self._on_add_node),
            ("✎ 编辑选中", self._on_edit_node),
            ("🗑 删除选中", self._on_delete_node),
            ("↑ 上移", self._on_move_up),
            ("↓ 下移", self._on_move_down),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            node_btn_row.addWidget(btn)
        node_btn_row.addStretch()
        right.addLayout(node_btn_row)

        # 树视图
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        right.addWidget(self.tree_view)

        # 模板操作按钮
        tpl_btn_row = QHBoxLayout()
        for text, slot in [
            ("📄 新建模板", self._on_new_template),
            ("💾 保存模板", self._on_save_template),
            ("🗑 删除模板", self._on_delete_template),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            tpl_btn_row.addWidget(btn)
        tpl_btn_row.addStretch()
        right.addLayout(tpl_btn_row)

        self.status_label = QLabel()
        right.addWidget(self.status_label)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_row.addWidget(close_btn)
        right.addLayout(close_row)

        right_widget = QWidget()
        right_widget.setLayout(right)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 640])
        layout.addWidget(splitter)

    # ────────────── 模板列表 ──────────────

    def _load_template_list(self):
        """按关键词加载模板列表（名称 / 类型匹配），不含系统模板。"""
        keyword = self.search_edit.text().strip()
        self.template_list.blockSignals(True)
        self.template_list.clear()
        for tmpl in self.scheduler.search_templates(keyword, include_system=False):
            item = QListWidgetItem(f"[{tmpl['type_label']}] {tmpl['name']}")
            item.setData(Qt.ItemDataRole.UserRole, tmpl)
            self.template_list.addItem(item)
        self.template_list.blockSignals(False)
        self.status_label.setText(f"模板总数: {self.template_list.count()}")

    def _on_template_selected(self, current, previous):
        """选中模板后加载其内容到树形编辑器。"""
        if current is None:
            self.current_filepath = None
            return
        tmpl = current.data(Qt.ItemDataRole.UserRole)
        self.current_filepath = tmpl["filepath"]
        self.name_label.setText(f"{tmpl['type_label']} / {tmpl['name']}  ({tmpl['filepath']})")
        self._load_tree_from_file(self.current_filepath)

    # ────────────── 树形编辑 ──────────────

    def _load_tree_from_file(self, filepath):
        """读取模板内容并构建树模型；解析失败时提示并退回空树。"""
        content = self.scheduler.get_template_content(filepath) or ""
        root = TreeNode("block", "(模板)")
        nodes = []
        if content.strip():
            try:
                nodes = parse_pdx_text_to_nodes(content.strip())
            except Exception:
                nodes = []
                QMessageBox.warning(self, "提示",
                                    "模板内容无法解析为树结构，可继续编辑（保存时将以文本追加）。")
        for node in nodes:
            root.add_child(node)
        self.model = FocusTreeModel(root, translator=None)
        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()


    def _current_node(self):
        """获取当前选中的树节点。"""
        index = self.tree_view.currentIndex()
        if not index.isValid() or self.model is None:
            return None
        return self.model.node_from_index(index)

    def _on_add_node(self):
        """添加子节点：调用树形编辑器的节点编辑窗口。"""
        if self.model is None:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        parent = self._current_node()
        if parent is None:
            parent = self.model.root_node
        from node_edit_dialog import NodeEditDialog
        dlg = NodeEditDialog(None, parent=self)
        dlg.setWindowTitle("添加节点")

        def on_ok():
            node = dlg.get_node()
            if node is None:
                dlg.deleteLater()
                return
            index = self.model.index_from_node(parent)
            self.model.add_node(node, index)
            self.tree_view.expandAll()
            dlg.deleteLater()

        dlg.accepted.connect(on_ok)
        dlg.show()

    def _on_edit_node(self):
        """编辑选中节点的键名/值/类型（调用树形编辑器的节点编辑窗口）。"""
        if self.model is None:
            return
        node = self._current_node()
        if node is None or node == self.model.root_node:
            QMessageBox.warning(self, "提示", "请先选择一个节点")
            return
        from node_edit_dialog import NodeEditDialog
        dlg = NodeEditDialog(None, node=node, parent=self)

        def on_ok():
            result = dlg.get_node()
            if result is not None:
                # 用结果节点替换原节点（保留子节点结构），并刷新视图
                self._replace_node(node, result)
                self.model.layoutChanged.emit()
            dlg.deleteLater()

        dlg.accepted.connect(on_ok)
        dlg.show()

    @staticmethod
    def _replace_node(node, result):
        """用新节点数据原地替换原节点属性（保持节点引用，避免索引失效）。"""
        node.key = result.key
        node.value = result.value
        node.node_type = result.node_type
        node.children = result.children
        node.raw_lines = []
        for child in node.children:
            child.parent = node

    def _on_delete_node(self):
        """删除选中的节点（根节点不可删除）。"""
        if self.model is None:
            return
        node = self._current_node()
        if node is None or node == self.model.root_node or node.parent is None:
            QMessageBox.warning(self, "提示", "请先选择一个子节点")
            return
        index = self.tree_view.currentIndex()
        self.model.remove_node(index)

    def _on_move_up(self):
        """上移选中的节点。"""
        if self.model is None:
            return
        node = self._current_node()
        if node is None or node.parent is None:
            return
        if node.move_up():
            index = self.model.index_from_node(node.parent)
            self.model.layoutChanged.emit()

    def _on_move_down(self):
        """下移选中的节点。"""
        if self.model is None:
            return
        node = self._current_node()
        if node is None or node.parent is None:
            return
        if node.move_down():
            index = self.model.index_from_node(node.parent)
            self.model.layoutChanged.emit()

    # ────────────── 模板操作 ──────────────

    def _serialize_tree(self) -> str:
        """将当前树序列化为 PDX 文本。"""
        if self.model is None:
            return ""
        parts = []
        for child in self.model.root_node.children:
            text = child.to_pdx(0)
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    def _on_new_template(self):
        """新建模板：输入名称与类型并创建空模板文件。"""
        name, ok = QInputDialog.getText(self, "新建模板", "模板名称:")
        if not ok or not (name or "").strip():
            return
        type_keys = list(TEMPLATE_TYPES.keys())
        type_labels = [TEMPLATE_TYPES[k]["name"] for k in type_keys]
        type_choice, ok2 = QInputDialog.getItem(self, "新建模板", "模板类型:",
                                                type_labels, editable=False)
        if not ok2:
            return
        ttype = type_keys[type_labels.index(type_choice)]

        path = self.scheduler.create_template(name.strip(), "", ttype)
        if not path:
            QMessageBox.warning(self, "错误", "创建模板失败")
            return
        self.current_filepath = path
        self._load_template_list()
        for i in range(self.template_list.count()):
            item = self.template_list.item(i)
            tmpl = item.data(Qt.ItemDataRole.UserRole)
            if tmpl and tmpl["filepath"] == path:
                self.template_list.setCurrentItem(item)
                break
        self._load_tree_from_file(path)
        QMessageBox.information(self, "成功", f"模板已创建：\n{path}")

    def _on_save_template(self):
        """保存当前树编辑内容到当前选中的模板文件。"""
        if not self.current_filepath:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        content = self._serialize_tree()
        try:
            os.makedirs(os.path.dirname(self.current_filepath), exist_ok=True)
            with open(self.current_filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
            return
        QMessageBox.information(self, "成功", "模板已保存")

    def _on_delete_template(self):
        """删除选中的模板文件。"""
        if not self.current_filepath:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        reply = QMessageBox.question(
            self, "确认", f"确定要删除模板 '{os.path.basename(self.current_filepath)}' 吗？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            os.remove(self.current_filepath)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败: {e}")
            return
        self.current_filepath = None
        self._load_template_list()
        self.templates_changed.emit()

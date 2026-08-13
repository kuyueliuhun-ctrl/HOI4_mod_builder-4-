"""模板管理对话框模块

提供 TemplateManagerDialog 及配套对话框：
- 左侧：模板文件列表（支持搜索）
- 右侧：树形编辑器（基于 TreeNode + FocusTreeModel）编辑模板内容
- 模板操作：新建/删除/保存模板
- 变量功能：扫描模板中的占位符（__变量名__），
  设置每个变量的中文说明与是否启用（使用时弹出填写框）
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTreeView,
    QMessageBox, QComboBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QTextEdit, QInputDialog,
    QSplitter, QWidget, QAbstractItemView
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
        self.var_label = QLabel()
        info_row.addWidget(self.var_label)
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
            ("🧹 变量设置", self._on_variable_settings),
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
        """按关键词加载模板列表（名称 / 类型 / 变量名匹配）。"""
        keyword = self.search_edit.text().strip()
        self.template_list.blockSignals(True)
        self.template_list.clear()
        for tmpl in self.scheduler.search_templates(keyword):
            content = self.scheduler.get_template_content(tmpl["filepath"]) or ""
            if keyword and keyword not in content:
                vars_found = [v for v in self.scheduler.scan_template_variables(content)
                              if keyword.lower() in v.lower()]
                if not vars_found:
                    continue
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
        self._update_var_label(filepath)

    def _update_var_label(self, filepath):
        """显示当前模板的变量数量。"""
        variables = self.scheduler.get_template_variables(filepath)
        enabled = [v for v in variables if v.get("enabled")]
        if variables:
            self.var_label.setText(f"变量 {len(enabled)}/{len(variables)} 启用")
        else:
            self.var_label.setText("无变量")

    def _current_node(self):
        """获取当前选中的树节点。"""
        index = self.tree_view.currentIndex()
        if not index.isValid() or self.model is None:
            return None
        return self.model.node_from_index(index)

    def _on_add_node(self):
        """添加子节点（简单对话框：类型/键名/值）。"""
        if self.model is None:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        parent = self._current_node()
        if parent is None:
            parent = self.model.root_node
        node = _NodeEditDialog(parent=self).get_result()
        if node is None:
            return
        index = self.model.index_from_node(parent)
        self.model.add_node(node, index)
        self.tree_view.expandAll()

    def _on_edit_node(self):
        """编辑选中节点的键名/值/类型。"""
        if self.model is None:
            return
        node = self._current_node()
        if node is None or node == self.model.root_node:
            QMessageBox.warning(self, "提示", "请先选择一个节点")
            return
        dlg = _NodeEditDialog(node=node, parent=self)
        node = dlg.get_result()
        if node is not None:
            self._load_tree_from_file(self.current_filepath)

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
        """新建模板：输入名称与类型，创建后自动弹出变量选择。"""
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

        # 创建空模板文件，再提示变量选择
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
        self._open_variable_dialog()
        QMessageBox.information(self, "成功", f"模板已创建：\n{path}\n\n"
                                              f"提示：在模板内容中填入 __变量名__ 占位符后，\n"
                                              f"点击「变量设置」选择使用时需要填写的变量。")

    def _on_save_template(self):
        """保存当前树编辑内容到模板文件。"""
        if not self.current_filepath:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        content = self._serialize_tree()
        try:
            os.makedirs(os.path.dirname(self.current_filepath), exist_ok=True)
            with open(self.current_filepath, "w", encoding="utf-8-sig") as f:
                f.write(content)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
            return
        # 保存后自动刷新变量配置（新出现的变量默认启用）
        self.scheduler.get_template_variables(self.current_filepath)
        self._update_var_label(self.current_filepath)
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

    # ────────────── 变量功能 ──────────────

    def _on_variable_settings(self):
        """打开变量设置对话框（扫描占位符，勾选启用，填写说明）。"""
        if not self.current_filepath:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        self._open_variable_dialog()

    def _open_variable_dialog(self):
        """弹出变量设置对话框并在确认后保存配置。"""
        dlg = TemplateVariableDialog(self.scheduler, self.current_filepath, parent=self)
        dlg.accepted.connect(self._update_var_label)
        dlg.accepted.connect(lambda: self._update_var_label(self.current_filepath))
        dlg.show()


class TemplateVariableDialog(QDialog):
    """模板变量设置对话框 - 非模态

    扫描模板内容中的 __变量名__ 占位符，
    为每个变量设置中文说明并勾选"使用时需要填入"。
    """

    def __init__(self, scheduler, filepath, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.filepath = filepath

        self.setWindowTitle(f"模板变量设置 - {os.path.basename(filepath)}")
        self.setMinimumSize(520, 400)
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("扫描到的占位符变量（勾选后，使用模板时提示填入）："))

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["使用时填入", "变量名", "中文说明"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self._variables = self.scheduler.get_template_variables(filepath)
        self.table.setRowCount(len(self._variables))
        for row, var in enumerate(self._variables):
            check = QCheckBox()
            check.setChecked(bool(var.get("enabled", True)))
            self.table.setCellWidget(row, 0, check)
            self.table.setItem(row, 1, QTableWidgetItem(var.get("name", "")))
            label_item = QTableWidgetItem(var.get("label", ""))
            self.table.setItem(row, 2, label_item)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        self.status_label.setText(f"共 {len(self._variables)} 个变量"
                                  if self._variables else "未发现变量（在模板内容中使用 __变量名__）")

    def _on_ok(self):
        """收集表格内容并保存变量配置。"""
        variables = []
        for row in range(self.table.rowCount()):
            check = self.table.cellWidget(row, 0)
            name_item = self.table.item(row, 1)
            label_item = self.table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            variables.append({
                "name": name,
                "label": label_item.text().strip() if label_item else "",
                "enabled": bool(check.isChecked()) if check else True,
            })
        if self.scheduler.set_template_variables(self.filepath, variables):
            self.status_label.setText("已保存")
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "保存变量配置失败")


class TemplateApplyDialog(QDialog):
    """模板变量填写对话框 - 使用模板时弹出

    展示模板中启用的变量，用户填写值后返回 {占位符: 值}。
    """

    def __init__(self, variables, parent=None):
        """Args:
            variables: [{"name", "label"}, ...]（已启用变量）
        """
        super().__init__(parent)
        self.variables = variables
        self._values = {}

        self.setWindowTitle("填写模板变量")
        self.setMinimumWidth(420)
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QFormLayout(self)
        self._edits = {}
        for var in variables:
            name = var.get("name", "")
            label = var.get("label") or name.strip("_")
            edit = QLineEdit()
            edit.setPlaceholderText(name)
            layout.addRow(f"{label}:", edit)
            self._edits[name] = edit

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addRow(btn_row)

    def _on_ok(self):
        for name, edit in self._edits.items():
            self._values[name] = edit.text().strip()
        self.accept()

    def get_values(self) -> dict:
        """获取填写的变量值 {占位符: 值}。"""
        return self._values


class _NodeEditDialog(QDialog):
    """简单节点编辑对话框：类型 / 键名 / 值。"""

    def __init__(self, node=None, parent=None):
        super().__init__(parent)
        self.node = node
        self._result = None

        self.setWindowTitle("编辑节点" if node else "添加节点")
        self.setMinimumWidth(380)
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QFormLayout(self)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["值节点 (value)", "块节点 (block)"])
        layout.addRow("类型:", self.type_combo)
        self.key_edit = QLineEdit()
        layout.addRow("键名:", self.key_edit)
        self.value_edit = QLineEdit()
        layout.addRow("值:", self.value_edit)

        if node:
            self.type_combo.setCurrentIndex(1 if node.node_type == "block" else 0)
            self.key_edit.setText(node.key)
            self.value_edit.setText(node.value)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addRow(btn_row)

    def _on_ok(self):
        node_type = "block" if self.type_combo.currentIndex() == 1 else "value"
        key = self.key_edit.text().strip()
        value = self.value_edit.text().strip()
        if node_type == "block":
            self._result = TreeNode("block", key or "(block)")
        else:
            self._result = TreeNode("value", key, value)
        self.accept()

    def get_result(self):
        """返回编辑后的节点，取消时为 None。"""
        if not self._result:
            return None
        return self._result

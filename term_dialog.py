"""词条管理对话框模块

提供 TermDialog 类，用于管理 HOI4 效果器/触发器词条。
词条包含：英文、中文、类型（触发器/效果器）、标签。

词条数据通过 TermRegistry 管理：
- 自动整理词条（source=common_code）只读展示
- 用户自定义词条（source=user）支持增删改查，保存到 translations/custom_terms.json
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFormLayout,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal

NODE_TYPE_NAMES = {"block": "块", "value": "值"}


class TermDialog(QDialog):
    """词条管理对话框 - 非模态

    以表格形式展示全部词条（自动整理 + 用户自定义），支持：
    - 按关键词/类型/标签筛选
    - 新增用户自定义词条
    - 编辑用户自定义词条
    - 删除用户自定义词条
    - 自动保存到 translations/custom_terms.json
    """

    terms_changed = pyqtSignal()

    def __init__(self, registry, parent=None):
        """初始化词条管理对话框

        Args:
            registry (TermRegistry): 词条注册表实例
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.registry = registry
        self._all_terms = []

        self.setWindowTitle("词条管理（块 / 值）")
        self.setMinimumSize(760, 500)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._reload()

    def _setup_ui(self):
        """构建 UI 布局。"""
        layout = QVBoxLayout(self)

        # ── 筛选行 ──
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("英文 / 中文 / 标签")
        self.search_edit.textChanged.connect(self._reload)
        filter_row.addWidget(self.search_edit)
        filter_row.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", "")
        self.type_combo.addItem("块", "block")
        self.type_combo.addItem("值", "value")
        self.type_combo.currentIndexChanged.connect(self._reload)
        filter_row.addWidget(self.type_combo)
        filter_row.addWidget(QLabel("标签:"))
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("如: 政治 / 经济 / 陆军")
        self.tag_edit.textChanged.connect(self._reload)
        filter_row.addWidget(self.tag_edit)
        layout.addLayout(filter_row)

        # ── 操作按钮 ──
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 新增词条")
        add_btn.clicked.connect(self._on_add)
        edit_btn = QPushButton("✎ 编辑选中")
        edit_btn.clicked.connect(self._on_edit)
        del_btn = QPushButton("🗑 删除选中")
        del_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── 词条表格 ──
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["英文", "中文", "类型", "标签", "来源", "描述"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(lambda *_: self._on_edit())
        layout.addWidget(self.table)

        # ── 状态标签 ──
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # ── 关闭按钮 ──
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _reload(self):
        """根据筛选条件重新加载表格。"""
        kw = self.search_edit.text().strip()
        node_type = self.type_combo.currentData() or None
        tag = self.tag_edit.text().strip() or None
        terms = self.registry.search(kw, node_type=node_type, tag=tag, limit=2000)
        self._all_terms = terms

        self.table.setRowCount(0)
        for term in terms:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(term.get("key", "")))
            self.table.setItem(row, 1, QTableWidgetItem(term.get("cn", "")))
            self.table.setItem(row, 2, QTableWidgetItem(
                NODE_TYPE_NAMES.get(term.get("node_type", "value"), term.get("node_type", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(
                "、".join(term.get("tags", []))))
            self.table.setItem(row, 4, QTableWidgetItem(
                "用户" if term.get("source") == "user" else "自动"))
            self.table.setItem(row, 5, QTableWidgetItem(term.get("description", "")))
            for col in range(6):
                item = self.table.item(row, col)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, term)

        counts = self.registry.counts()
        self.status_label.setText(
            f"共 {len(terms)} 条 | 块 {counts['block']} / 值 {counts['value']}")

    def _selected_term(self):
        """获取当前选中行对应的词条。"""
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_add(self):
        """新增用户自定义词条。"""
        dlg = _TermEditDialog(None, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.registry.add_user_term(
                data["key"], data["cn"], data["node_type"], data["tags"], data["description"])
            self.terms_changed.emit()
            self._reload()

    def _on_edit(self):
        """编辑选中的用户自定义词条（自动整理词条只读）。"""
        term = self._selected_term()
        if not term:
            QMessageBox.information(self, "提示", "请先选择一个词条")
            return
        if term.get("source") != "user":
            QMessageBox.information(
                self, "提示",
                "该词条由常用代码自动整理，不可编辑。\n"
                "如需修改，请新增同名用户词条覆盖，或编辑 translations/effect_terms.json。")
            return
        dlg = _TermEditDialog(term, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.registry.update_user_term(
                data["key"], data["cn"], data["node_type"], data["tags"], data["description"])
            self.terms_changed.emit()
            self._reload()

    def _on_delete(self):
        """删除选中的用户自定义词条。"""
        term = self._selected_term()
        if not term:
            QMessageBox.information(self, "提示", "请先选择一个词条")
            return
        if term.get("source") != "user":
            QMessageBox.information(self, "提示", "自动整理词条不可删除")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除词条 '{term.get('key')}' 吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.registry.remove_user_term(term.get("key", ""))
            self.terms_changed.emit()
            self._reload()


class _TermEditDialog(QDialog):
    """词条编辑对话框：编辑英文/中文/类型/标签/描述。"""

    def __init__(self, term=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑词条" if term else "新增词条")
        self.setMinimumSize(460, 320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("英文命令名，如 add_political_power")
        form.addRow("英文:", self.key_edit)

        self.cn_edit = QLineEdit()
        self.cn_edit.setPlaceholderText("中文翻译")
        form.addRow("中文:", self.cn_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItem("值", "value")
        self.type_combo.addItem("块", "block")
        form.addRow("类型:", self.type_combo)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("用 / 分隔，如 政治/经济")
        form.addRow("标签:", self.tags_edit)

        self.desc_edit = QLineEdit()
        form.addRow("描述:", self.desc_edit)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

        if term:
            self.key_edit.setText(term.get("key", ""))
            self.cn_edit.setText(term.get("cn", ""))
            idx = self.type_combo.findData(term.get("node_type", "value"))
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.tags_edit.setText("、".join(term.get("tags", [])))
            self.desc_edit.setText(term.get("description", ""))

    def _on_ok(self):
        if not self.key_edit.text().strip():
            QMessageBox.warning(self, "错误", "英文命令名不能为空")
            return
        if not self.cn_edit.text().strip():
            QMessageBox.warning(self, "错误", "中文翻译不能为空")
            return
        self.accept()

    def get_data(self):
        """返回编辑后的词条数据。"""
        tags = [t.strip() for t in self.tags_edit.text().replace("、", "/")
                .replace("，", "/").split("/") if t.strip()]
        return {
            "key": self.key_edit.text().strip(),
            "cn": self.cn_edit.text().strip(),
            "node_type": self.type_combo.currentData(),
            "tags": tags,
            "description": self.desc_edit.text().strip(),
        }

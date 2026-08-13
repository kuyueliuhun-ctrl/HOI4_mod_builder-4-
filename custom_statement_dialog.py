"""自定义语句管理对话框模块

提供 CustomStatementDialog 和 _StatementEditDialog 两个类，
用于管理自定义 PDX 语句（命令）的定义和翻译。

自定义语句允许用户扩展 PDX 命令翻译库，为项目特定的命令
提供中文翻译、默认值、值翻译映射等配置。

升级说明（文件视图）：
- 左侧列出所有可编辑的翻译文件（用户自定义语句文件 + translations 目录中含 statements 的 JSON 文件）
- 右侧表格展示当前选中文件中的语句，增删改直接写入该文件
- 同时同步翻译器内存（custom_statements），保证翻译即时生效
"""

import json
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit,
    QMessageBox, QComboBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem,
    QSplitter, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal


class CustomStatementDialog(QDialog):
    """自定义语句管理对话框 - 非模态（文件视图版）

    左侧：翻译文件列表（用户自定义语句文件 + translations 目录中含 statements 的 JSON 文件）
    右侧：当前选中文件中的语句表格，支持添加/编辑/删除，直接写入选中文件。

    Attributes:
        translator (GuiTranslator): 翻译器实例，管理自定义语句数据
        custom_path (str): 用户自定义语句配置文件的保存路径
        table (QTableWidget): 显示语句列表的表格控件
    """

    # 信号：自定义语句列表发生变更时通知外部
    statements_changed = pyqtSignal()

    def __init__(self, translator, custom_path, parent=None):
        """初始化自定义语句管理对话框

        Args:
            translator (GuiTranslator): 翻译器实例
            custom_path (str): 自定义语句配置文件保存路径
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.translator = translator
        self.custom_path = custom_path

        self.setWindowTitle("自定义语句管理")
        self.setMinimumSize(820, 500)
        # 非模态窗口
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._files = []          # [(显示名, 文件路径), ...]
        self._current_file = None  # 当前选中的文件路径

        self._setup_ui()
        self._scan_statement_files()
        self._load_statements()

    # ────────────── UI 构建 ──────────────

    def _setup_ui(self):
        """构建 UI 布局

        布局结构：
        左侧：文件列表（已有翻译文件）
        右侧：操作按钮行 + 语句表格 + 状态标签 + 关闭按钮
        """
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 左侧：翻译文件列表 ──
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(0, 0, 0, 0)
        file_label = QLabel("翻译文件")
        left_panel.addWidget(file_label)
        self.file_list = QListWidget()
        self.file_list.setMinimumWidth(220)
        self.file_list.currentItemChanged.connect(self._on_file_changed)
        left_panel.addWidget(self.file_list)
        left_widget = QWidget()
        left_widget.setLayout(left_panel)

        # ── 右侧：语句表格 ──
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("语句名 / 中文翻译 / 描述…")
        self.search_edit.textChanged.connect(self._load_statements)
        search_row.addWidget(self.search_edit)
        right_panel.addLayout(search_row)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ 添加新语句")
        add_btn.clicked.connect(self._on_add)
        edit_btn = QPushButton("✎ 编辑选中")
        edit_btn.clicked.connect(self._on_edit)
        del_btn = QPushButton("🗑 删除选中")
        del_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        right_panel.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["PDX键名", "中文翻译", "类型", "默认值", "描述"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_panel.addWidget(self.table)

        self.status_label = QLabel()
        right_panel.addWidget(self.status_label)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        right_panel.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 560])
        main_layout.addWidget(splitter)

    # ────────────── 文件扫描与加载 ──────────────

    def _scan_statement_files(self):
        """扫描可编辑的翻译文件

        文件来源：
        1. 用户自定义语句文件（custom_statement_path）
        2. translations 目录中所有含 statements 数组的 JSON 文件
        """
        self._files = []
        self.file_list.clear()

        items = []
        if self.custom_path and os.path.isfile(self.custom_path):
            items.append((os.path.basename(self.custom_path) + " (用户)", self.custom_path))
        try:
            from translation_loader import get_translations_dir
            trans_dir = get_translations_dir()
        except Exception:
            trans_dir = ""
        if trans_dir and os.path.isdir(trans_dir):
            for fn in sorted(os.listdir(trans_dir)):
                if not fn.endswith(".json"):
                    continue
                fp = os.path.join(trans_dir, fn)
                if self.custom_path and os.path.abspath(fp) == os.path.abspath(self.custom_path):
                    continue
                if self._file_has_statements(fp):
                    items.append((fn, fp))

        self._files = items
        for name, path in items:
            count = len(self._load_file_statements(path))
            self.file_list.addItem(QListWidgetItem(f"{name}  ({count} 条)"))

    @staticmethod
    def _file_has_statements(path):
        """判断文件是否为含 statements 数组的 JSON 文件"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return isinstance(data, dict) and isinstance(data.get("statements"), list)
        except Exception:
            return False

    @staticmethod
    def _load_file_statements(path):
        """读取文件中的 statements 数组（不经过加载器合并）"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("statements"), list):
                return data["statements"]
        except Exception:
            pass
        return []

    @staticmethod
    def _save_file_statements(path, statements):
        """将 statements 写回指定文件（保留文件其它顶层键）"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        data["statements"] = statements
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _current_path(self):
        """获取当前选中文件的路径"""
        row = self.file_list.currentRow()
        if 0 <= row < len(self._files):
            return self._files[row][1]
        return self.custom_path if self._files else None

    # ────────────── 数据展示 ──────────────

    def _on_file_changed(self, current, previous):
        """切换文件时刷新右侧语句表格"""
        if current is not None:
            self._load_statements()

    def _load_statements(self):
        """加载当前选中文件中的语句并填充表格（支持关键词过滤）"""
        path = self._current_path()
        statements = self._load_file_statements(path) if path else []
        keyword = self.search_edit.text().strip().lower() if hasattr(self, "search_edit") else ""
        if keyword:
            filtered = []
            for stmt in statements:
                haystack = " ".join([
                    str(stmt.get("key", "")),
                    str(stmt.get("cn_name", "")),
                    str(stmt.get("description", "")),
                    str(stmt.get("default_value", "")),
                ]).lower()
                if keyword in haystack:
                    filtered.append(stmt)
            statements = filtered
        self._current_file = path
        self.table.setRowCount(0)
        for stmt in statements:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(stmt.get("key", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(stmt.get("cn_name", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(
                "块" if stmt.get("node_type") == "block" else "值"
            ))
            self.table.setItem(row, 3, QTableWidgetItem(str(stmt.get("default_value", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(str(stmt.get("description", ""))))
        self._update_status(len(statements))

    def _update_status(self, count):
        """更新状态标签：显示当前文件与语句数量"""
        name = os.path.basename(self._current_path()) if self._current_path else ""
        self.status_label.setText(f"文件 {name}：共 {count} 条语句")

    def _get_selected_key(self):
        """获取当前选中行的 PDX 键名

        Returns:
            str or None: 选中行的键名，无选中时返回 None
        """
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择一条语句")
            return None
        row = selected[0].row()
        return self.table.item(row, 0).text()

    # ────────────── 增删改 ──────────────

    def _on_add(self):
        """打开添加自定义语句对话框"""
        dlg = _StatementEditDialog(self.translator, parent=self)
        dlg.accepted.connect(lambda: self._on_edit_dialog_ok(dlg))
        dlg.show()

    def _on_edit(self):
        """打开编辑自定义语句对话框"""
        key = self._get_selected_key()
        if not key:
            return
        path = self._current_path()
        stmt = None
        for s in self._load_file_statements(path) if path else []:
            if s.get("key") == key:
                stmt = s
                break
        if not stmt:
            return
        dlg = _StatementEditDialog(self.translator, stmt=stmt, parent=self)
        dlg.accepted.connect(lambda: self._on_edit_dialog_ok(dlg, old_key=key))
        dlg.show()

    def _on_edit_dialog_ok(self, dlg, old_key=None):
        """处理编辑对话框的确认结果

        更新选中文件中的语句并持久化，同步翻译器内存。
        """
        path = self._current_path()
        stmt = dlg.get_statement()
        statements = self._load_file_statements(path) if path else []

        # 键名变更时移除旧键
        if old_key and old_key != stmt["key"]:
            statements = [s for s in statements if s.get("key") != old_key]
            if self.translator.custom_statements.get(old_key):
                self.translator.remove_custom_statement(old_key)
        # 更新或追加
        for i, s in enumerate(statements):
            if s.get("key") == stmt["key"]:
                statements[i] = stmt
                break
        else:
            statements.append(stmt)

        # 同步翻译器内存
        self.translator.add_custom_statement(**stmt)
        # 持久化到选中文件
        if path:
            self._save_file_statements(path, statements)
        # 刷新表格与文件列表计数
        self._load_statements()
        self._refresh_file_counts()
        # 通知外部数据变更
        self.statements_changed.emit()
        dlg.deleteLater()

    def _on_delete(self):
        """删除选中的自定义语句

        二次确认后从当前文件与翻译器内存中移除并保存。
        """
        key = self._get_selected_key()
        if not key:
            return
        reply = QMessageBox.question(self, "确认", f"确定要删除语句 '{key}' 吗？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        path = self._current_path()
        statements = self._load_file_statements(path) if path else []
        statements = [s for s in statements if s.get("key") != key]
        if self.translator.custom_statements.get(key):
            self.translator.remove_custom_statement(key)
        if path:
            self._save_file_statements(path, statements)
        self._load_statements()
        self._refresh_file_counts()
        self.statements_changed.emit()

    def _refresh_file_counts(self):
        """刷新左侧文件列表的语句计数（不重置选中）"""
        current_name = self.file_list.currentItem().text() if self.file_list.currentItem() else ""
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for name, path in self._files:
            count = len(self._load_file_statements(path))
            item = QListWidgetItem(f"{name}  ({count} 条)")
            self.file_list.addItem(item)
            if current_name and current_name.startswith(name):
                self.file_list.setCurrentItem(item)
        self.file_list.blockSignals(False)


class _StatementEditDialog(QDialog):
    """自定义语句编辑子对话框 - 非模态

    用于添加或编辑单条自定义 PDX 语句的定义，
    包括键名、中文翻译、节点类型、默认值、值翻译映射和描述。

    下划线前缀表示这是模块内部使用的私有类。

    Attributes:
        translator (GuiTranslator): 翻译器实例
        stmt (dict, optional): 编辑模式下的现有语句数据
        _result (dict): 确认后生成的语句数据字典
    """

    def __init__(self, translator, stmt=None, parent=None):
        """初始化语句编辑对话框

        Args:
            translator (GuiTranslator): 翻译器实例
            stmt (dict, optional): 现有语句数据，None 表示新建模式
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.translator = translator
        self.stmt = stmt

        self.setWindowTitle("编辑自定义语句" if stmt else "添加自定义语句")
        self.setMinimumSize(450, 350)
        # 非模态窗口
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        if stmt:
            self._load_stmt(stmt)

    def _setup_ui(self):
        """构建 UI 布局

        使用 QFormLayout 组织表单字段：
        - PDX键名*（必填）
        - 中文翻译*（必填）
        - 节点类型*（下拉选择：值/块）
        - 默认值（可选）
        - 值翻译（可选，支持多行 key=value 格式）
        - 描述备注（可选）
        - 确定/取消按钮
        """
        layout = QFormLayout(self)

        layout.addRow(QLabel("PDX键名*:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("英文PDX命令名（如 my_custom_effect）")
        layout.addRow(self.key_edit)

        layout.addRow(QLabel("中文翻译*:"))
        self.cn_edit = QLineEdit()
        self.cn_edit.setPlaceholderText("如 我的自定义效果")
        layout.addRow(self.cn_edit)

        layout.addRow(QLabel("节点类型*:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["值节点 (value)", "块节点 (block)"])
        layout.addRow(self.type_combo)

        layout.addRow(QLabel("默认值:"))
        self.default_edit = QLineEdit()
        self.default_edit.setPlaceholderText("可选，新建节点时自动填充")
        layout.addRow(self.default_edit)

        layout.addRow(QLabel("值翻译 (每行一条，格式: 英文值=中文翻译):"))
        self.vt_edit = QTextEdit()
        self.vt_edit.setPlaceholderText("如:\nmy_idea_1 = 我的理念1\nmy_idea_2 = 我的理念2")
        self.vt_edit.setMaximumHeight(100)
        layout.addRow(self.vt_edit)

        layout.addRow(QLabel("描述备注:"))
        self.desc_edit = QLineEdit()
        layout.addRow(self.desc_edit)

        # ── 按钮行 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addRow(btn_layout)

    def _load_stmt(self, stmt):
        """将现有语句数据加载到表单控件

        Args:
            stmt (dict): 语句数据字典，包含 key, cn_name, node_type,
                         default_value, description, value_translations
        """
        self.key_edit.setText(str(stmt.get("key", "")))
        self.cn_edit.setText(str(stmt.get("cn_name", "")))
        # 根据节点类型设置下拉框索引
        if stmt.get("node_type") == "block":
            self.type_combo.setCurrentIndex(1)  # 块节点
        else:
            self.type_combo.setCurrentIndex(0)  # 值节点
        self.default_edit.setText(str(stmt.get("default_value", "")))
        self.desc_edit.setText(str(stmt.get("description", "")))

        # 加载值翻译映射
        vt = stmt.get("value_translations", {})
        if vt:
            lines = [f"{k} = {v}" for k, v in vt.items()]
            self.vt_edit.setPlainText("\n".join(lines))

    def _on_ok(self):
        """确认编辑，构建结果数据

        验证必填字段（PDX键名和中文翻译）后，
        构建包含所有字段的字典并调用 accept()。
        """
        key = self.key_edit.text().strip()
        cn = self.cn_edit.text().strip()

        # 必填字段验证
        if not key or not cn:
            QMessageBox.warning(self, "错误", "PDX键名和中文翻译为必填项")
            return

        self._result = {
            "key": key,
            "cn_name": cn,
            # combo 索引 1 → block，索引 0 → value
            "node_type": "block" if self.type_combo.currentIndex() == 1 else "value",
            "default_value": self.default_edit.text().strip(),
            "value_translations": self._parse_vt(),
            "description": self.desc_edit.text().strip(),
        }
        # 触发 accepted 信号并关闭对话框
        self.accept()

    def _parse_vt(self) -> dict:
        """解析值翻译文本区域的内容

        将 "英文值=中文翻译" 格式的每行文本解析为字典。
        行格式示例: my_idea_1 = 我的理念1

        Returns:
            dict: 英文值到中文翻译的映射字典
        """
        result = {}
        text = self.vt_edit.toPlainText().strip()
        if not text:
            return result
        for line in text.split("\n"):
            line = line.strip()
            if "=" in line:
                # 按第一个等号分割，避免值中包含等号时出错
                parts = line.split("=", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                if k and v:
                    result[k] = v
        return result

    def get_statement(self) -> dict:
        """获取编辑后的语句数据

        Returns:
            dict: 包含完整语句定义的字典
        """
        return self._result

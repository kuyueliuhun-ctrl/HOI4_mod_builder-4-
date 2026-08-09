"""自定义语句管理对话框模块

提供 CustomStatementDialog 和 _StatementEditDialog 两个类，
用于管理自定义 PDX 语句（命令）的定义和翻译。

自定义语句允许用户扩展 PDX 命令翻译库，为项目特定的命令
提供中文翻译、默认值、值翻译映射等配置。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit,
    QMessageBox, QComboBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal


class CustomStatementDialog(QDialog):
    """自定义语句管理对话框 - 非模态

    以表格形式展示所有自定义的 PDX 语句，支持：
    - 添加新的自定义语句定义
    - 编辑现有自定义语句
    - 删除自定义语句
    - 自动保存到配置文件

    每条语句包含：PDX键名、中文翻译、节点类型、默认值、描述。
    语句数据通过 GuiTranslator 管理，保存到 custom_statement_path 指定的文件。

    Attributes:
        translator (GuiTranslator): 翻译器实例，管理自定义语句数据
        custom_path (str): 自定义语句配置文件的保存路径
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
        self.setMinimumSize(600, 450)
        # 非模态窗口
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        # 加载现有自定义语句到表格
        self._load_statements()

    def _setup_ui(self):
        """构建 UI 布局

        布局结构：
        1. 操作按钮行：添加 / 编辑 / 删除
        2. 表格：展示所有自定义语句（PDX键名、中文翻译、类型、默认值、描述）
        3. 状态标签
        4. 关闭按钮（右下角）
        """
        layout = QVBoxLayout(self)

        # ── 操作按钮 ──
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
        layout.addLayout(btn_layout)

        # ── 语句表格 ──
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["PDX键名", "中文翻译", "类型", "默认值", "描述"])
        # 设置列宽策略：拉伸填充，类型列自适应内容
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        # 禁止直接编辑单元格（通过弹窗编辑）
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 整行选中
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # ── 状态标签 ──
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # ── 关闭按钮 ──
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_statements(self):
        """从翻译器加载自定义语句并填充表格

        清空现有表格数据，遍历 translator.custom_statements 字典，
        为每条语句创建一行数据。
        """
        self.table.setRowCount(0)  # 清空所有行
        for key, stmt in self.translator.custom_statements.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(key))
            self.table.setItem(row, 1, QTableWidgetItem(stmt.get("cn_name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(
                "块" if stmt.get("node_type") == "block" else "值"
            ))
            self.table.setItem(row, 3, QTableWidgetItem(str(stmt.get("default_value", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(stmt.get("description", "")))
        self._update_status()

    def _update_status(self):
        """更新状态标签：显示已定义的自定义语句数量"""
        count = len(self.translator.custom_statements)
        self.status_label.setText(f"已定义 {count} 条自定义语句")

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

    def _on_add(self):
        """打开添加自定义语句对话框

        创建 _StatementEditDialog 并连接确认信号，
        确认后通过 _on_edit_dialog_ok 保存新语句。
        """
        dlg = _StatementEditDialog(self.translator, parent=self)
        dlg.accepted.connect(lambda: self._on_edit_dialog_ok(dlg))
        dlg.show()

    def _on_edit(self):
        """打开编辑自定义语句对话框

        获取选中的语句键名，从翻译器中读取现有数据，
        传入 _StatementEditDialog 进行编辑。
        """
        key = self._get_selected_key()
        if not key:
            return
        stmt = self.translator.custom_statements.get(key)
        if not stmt:
            return
        dlg = _StatementEditDialog(self.translator, stmt=stmt, parent=self)
        dlg.accepted.connect(lambda: self._on_edit_dialog_ok(dlg, old_key=key))
        dlg.show()

    def _on_edit_dialog_ok(self, dlg, old_key=None):
        """处理编辑对话框的确认结果

        如果键名发生了变化，先删除旧的键名再添加。
        保存到翻译器并持久化到文件，最后刷新表格。

        Args:
            dlg (_StatementEditDialog): 编辑对话框实例
            old_key (str, optional): 编辑前的旧键名
        """
        stmt = dlg.get_statement()
        # 如果键名变更，移除旧键
        if old_key and old_key != stmt["key"]:
            self.translator.remove_custom_statement(old_key)
        # 添加/更新自定义语句
        self.translator.add_custom_statement(**stmt)
        # 持久化保存到文件
        self.translator.save_custom_statements(self.custom_path)
        # 刷新表格显示
        self._load_statements()
        # 通知外部数据变更
        self.statements_changed.emit()
        dlg.deleteLater()

    def _on_delete(self):
        """删除选中的自定义语句

        二次确认后从翻译器中移除，保存并刷新表格。
        """
        key = self._get_selected_key()
        if not key:
            return
        reply = QMessageBox.question(self, "确认", f"确定要删除语句 '{key}' 吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.translator.remove_custom_statement(key)
            self.translator.save_custom_statements(self.custom_path)
            self._load_statements()
            self.statements_changed.emit()

    def _on_close(self):
        """关闭对话框"""
        self.close()


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
        self.key_edit.setText(stmt.get("key", ""))
        self.cn_edit.setText(stmt.get("cn_name", ""))
        # 根据节点类型设置下拉框索引
        if stmt.get("node_type") == "block":
            self.type_combo.setCurrentIndex(1)  # 块节点
        else:
            self.type_combo.setCurrentIndex(0)  # 值节点
        self.default_edit.setText(str(stmt.get("default_value", "")))
        self.desc_edit.setText(stmt.get("description", ""))

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

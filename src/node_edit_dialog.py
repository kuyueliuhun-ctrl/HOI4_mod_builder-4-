"""PDX 节点编辑对话框模块

提供 NodeEditDialog 类，用于创建或编辑 PDX 树中的节点（值节点或块节点）。
对话框支持：
- 节点类型选择（值节点 / 块节点）
- 键名搜索（通过翻译器查找 PDX 命令）
- 值搜索和选择
- 中文翻译实时预览
- 高级模式：直接输入原始 PDX 文本
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QButtonGroup, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QMessageBox,
    QFormLayout, QFrame
)
from PyQt6.QtCore import Qt
from tree_node import TreeNode


class NodeEditDialog(QDialog):
    """节点编辑对话框 - 非模态

    提供创建/编辑 PDX 树节点的界面，支持：
    - 选择节点类型（值节点: key = value, 块节点: key = { ... }）
    - 通过翻译器搜索 PDX 命令名（支持中英文模糊搜索）
    - 值搜索：搜索可能的合法值
    - 中文翻译实时预览
    - 高级直接编辑模式：输入原始 PDX 文本

    Attributes:
        translator (GuiTranslator): 翻译器实例，提供命令搜索和翻译
        node (TreeNode, optional): 编辑模式下传入的已有节点
        result_node (TreeNode): 对话框确认后生成的结果节点
    """

    def __init__(self, translator, node=None, parent=None, default_type="value",
                 preset_key=""):
        """初始化节点编辑对话框

        Args:
            translator (GuiTranslator): 翻译器实例
            node (TreeNode, optional): 要编辑的现有节点，None 表示新建模式
            parent (QWidget, optional): 父窗口
            default_type (str): 默认节点类型，"value" 或 "block"
            preset_key (str): 预填键名（创建模式下使用）
        """
        super().__init__(parent)
        self.translator = translator
        self.node = node
        self._preset_key = preset_key
        # 确认后生成的结果节点
        self.result_node = None
        # 搜索结果缓存
        self._search_results = []
        self._value_search_results = []

        # 根据模式设置标题
        self.setWindowTitle("编辑节点" if node else "添加节点")
        self.setMinimumSize(560, 600)
        # 非模态窗口
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui(default_type)
        # 如果是编辑模式，加载现有节点数据
        if node:
            self._load_node(node)
        elif preset_key:
            self.key_edit.setText(preset_key)
            self._update_key_label()

    def _setup_ui(self, default_type):
        """构建 UI 布局

        布局结构（自上而下）：
        1. 节点类型选择（单选按钮组：值节点 / 块节点）
        2. 键名搜索区：搜索输入 + 搜索结果列表
        3. 键名输入区：键名编辑 + 中文翻译预览
        4. 值编辑区（仅在值节点模式下可见）：值搜索 + 值输入 + 翻译预览
        5. 底部按钮：高级编辑 / 取消 / 确定

        Args:
            default_type (str): 默认节点类型
        """
        layout = QVBoxLayout(self)

        # ── 节点类型选择 ──
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("节点类型:"))
        self.type_group = QButtonGroup(self)
        self.type_value_rb = QRadioButton("值节点")
        self.type_block_rb = QRadioButton("块节点")
        self.type_group.addButton(self.type_value_rb, 0)
        self.type_group.addButton(self.type_block_rb, 1)
        type_layout.addWidget(self.type_value_rb)
        type_layout.addWidget(self.type_block_rb)
        type_layout.addStretch()
        # 根据默认类型设置选中状态
        if default_type == "block":
            self.type_block_rb.setChecked(True)
        else:
            self.type_value_rb.setChecked(True)
        layout.addLayout(type_layout)

        # ── 键名搜索和输入区 ──
        key_form = QFormLayout()
        # 搜索框
        key_search_layout = QHBoxLayout()
        self.key_search_edit = QLineEdit()
        self.key_search_edit.setPlaceholderText("搜索PDX命令（中文/英文）...")
        self.key_search_edit.textChanged.connect(self._on_key_search)
        key_search_layout.addWidget(self.key_search_edit)
        key_form.addRow("🔍 键名搜索:", key_search_layout)

        # 搜索结果列表
        self.key_results_list = QListWidget()
        self.key_results_list.setMinimumHeight(120)
        self.key_results_list.setMaximumHeight(200)
        self.key_results_list.itemClicked.connect(self._on_key_selected)
        layout.addWidget(self.key_results_list)

        # 键名直接输入
        key_input_layout = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("输入PDX键名（英文）")
        key_input_layout.addWidget(self.key_edit)
        # 中文翻译实时预览
        self.key_cn_label = QLabel("")
        self.key_cn_label.setStyleSheet("color: #5d6b7a; font-size: 11px;")
        key_input_layout.addWidget(self.key_cn_label)
        self.key_edit.textChanged.connect(self._on_key_changed)
        key_form.addRow("键名:", key_input_layout)
        layout.addLayout(key_form)

        # ── 值编辑区（仅值节点时可见） ──
        self.value_group = QFrame()
        value_layout = QVBoxLayout(self.value_group)
        value_layout.setContentsMargins(0, 0, 0, 0)

        # 值搜索
        val_search_layout = QHBoxLayout()
        self.val_search_edit = QLineEdit()
        self.val_search_edit.setPlaceholderText("搜索值（中文/英文，可选）...")
        self.val_search_edit.textChanged.connect(self._on_val_search)
        val_search_layout.addWidget(self.val_search_edit)
        value_layout.addLayout(val_search_layout)

        # 值搜索结果列表
        self.val_results_list = QListWidget()
        self.val_results_list.setMinimumHeight(120)
        self.val_results_list.setMaximumHeight(200)
        self.val_results_list.itemClicked.connect(self._on_val_selected)
        value_layout.addWidget(self.val_results_list)

        # 值输入
        val_form = QFormLayout()
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("输入值（英文PDX标识符）")
        val_form.addRow("值:", self.value_edit)
        # 值的翻译预览
        self.val_cn_label = QLabel("")
        self.val_cn_label.setStyleSheet("color: #5d6b7a; font-size: 11px;")
        val_form.addRow("", self.val_cn_label)
        value_layout.addLayout(val_form)

        self.value_edit.textChanged.connect(self._on_val_changed)
        layout.addWidget(self.value_group)

        # 节点类型切换时控制值编辑区的显隐
        self.type_value_rb.toggled.connect(self._on_type_changed)

        # ── 底部按钮 ──
        btn_layout = QHBoxLayout()
        self.advanced_btn = QPushButton("高级: 直接编辑")
        self.advanced_btn.clicked.connect(self._on_advanced)
        btn_layout.addWidget(self.advanced_btn)
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _on_type_changed(self):
        """节点类型切换时控制值编辑区的显隐

        值节点需要编辑 value 字段，块节点不需要（其 value 为子节点树）。
        """
        is_value = self.type_value_rb.isChecked()
        self.value_group.setVisible(is_value)

    def _load_node(self, node):
        """将现有节点数据加载到表单控件中

        Args:
            node (TreeNode): 要编辑的现有节点
        """
        self.key_edit.setText(node.key)
        if node.node_type == "block":
            self.type_block_rb.setChecked(True)
        else:
            self.type_value_rb.setChecked(True)
            self.value_edit.setText(node.value)
        self._update_key_label()
        self._update_val_label()

    def _on_key_changed(self):
        """键名输入变化时更新翻译预览"""
        self._update_key_label()

    def _update_key_label(self):
        """更新键名的中文翻译预览标签

        通过翻译器的 translate_key 方法查找键名对应的中文翻译。
        有翻译：显示 "(中文翻译)"；无翻译：显示 "(未翻译)"。
        """
        key = self.key_edit.text().strip()
        if key:
            if not self.translator:
                self.key_cn_label.setText("")
                return
            cn = self.translator.translate_key(key)
            if cn != key:
                self.key_cn_label.setText(f"({cn})")
            else:
                self.key_cn_label.setText("(未翻译)")
        else:
            self.key_cn_label.setText("")

    def _on_val_changed(self):
        """值输入变化时更新翻译预览"""
        self._update_val_label()

    def _update_val_label(self):
        """更新值的中文翻译预览标签

        通过翻译器的 translate_value 方法查找值对应的中文翻译。
        有翻译：显示 "(中文翻译)"；无翻译：不显示。
        """
        val = self.value_edit.text().strip()
        if val:
            if not self.translator:
                self.val_cn_label.setText("")
                return
            cn = self.translator.translate_value(val)
            if cn != val:
                self.val_cn_label.setText(f"({cn})")
            else:
                self.val_cn_label.setText("")
        else:
            self.val_cn_label.setText("")

    def _on_key_search(self, text):
        """键名搜索：根据输入文本搜索匹配的 PDX 命令

        使用翻译器的 search 方法进行模糊搜索，
        结果同时匹配中文和英文，最多显示 50 条。
        自定义语句用 📌 前缀标识；词条显示类型；模板用 📄 前缀。

        Args:
            text (str): 搜索关键词
        """
        self.key_results_list.clear()
        self._search_results = []
        if not text.strip():
            return
        # 通过翻译器搜索（含词条与模板合并结果）
        if not self.translator:
            return
        results = self.translator.search_with_terms(text.strip())
        self._search_results = results
        for r in results[:50]:
            cn = r["cn"]
            key = r["key"]
            source = r["source"]
            # 自定义语句加特殊前缀标记
            if source == "custom":
                prefix = "📌"
            elif source == "term":
                ttype = "块" if r.get("type") == "block" else "值"
                prefix = f"{ttype}"
            elif source == "template":
                prefix = "📄"
            else:
                prefix = ""
            item = QListWidgetItem(f"{prefix} {cn} ........ {key}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.key_results_list.addItem(item)

    def _on_key_selected(self, item):
        """键名搜索结果被选中时，填入键名输入框

        词条/普通命令直接填入键名；模板则解析模板内容，直接将整个模板块作为结果节点。
        """
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("source") == "template" and data.get("filepath"):
            from template_scheduler import get_template_scheduler
            from tree_node import tree_from_pdx_text
            scheduler = get_template_scheduler()
            content = scheduler.get_template_content(data["filepath"]) or ""
            try:
                node = tree_from_pdx_text(content)
                if node.children:
                    # 直接将模板第一个块/值节点作为结果，无需再手动填入键名
                    self.result_node = node.children[0].clone()
                    self.accept()
                    return
            except Exception:
                pass
            self.key_edit.setText(data["key"])
            # 刷新搜索结果（保持列表可见）
            self._on_key_search(self.key_search_edit.text())
            return
        self.key_edit.setText(data["key"])
        # 刷新搜索结果（保持列表可见）
        self._on_key_search(self.key_search_edit.text())

    def _on_val_search(self, text):
        """值搜索：根据输入文本搜索可能的值选项

        与键名搜索类似，使用翻译器搜索系统，
        结果同时匹配中文和英文，最多显示 50 条。

        Args:
            text (str): 搜索关键词
        """
        self.val_results_list.clear()
        self._value_search_results = []
        if not text.strip():
            return
        results = self.translator.search(text.strip()) if self.translator else []
        self._value_search_results = results
        for r in results[:50]:
            cn = r["cn"]
            key = r["key"]
            item = QListWidgetItem(f"{cn} ........ {key}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.val_results_list.addItem(item)

    def _on_val_selected(self, item):
        """值搜索结果被选中时，填入值输入框"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.value_edit.setText(data["key"])

    def _on_advanced(self):
        """打开高级编辑模式

        弹出一个包含 QTextEdit 的对话框，允许用户直接输入
        原始的 PDX 行格式文本（如 key = value），
        确认后自动解析并填入键名和值输入框。
        """
        # 构建当前输入预览
        key_text = self.key_edit.text().strip()
        val_text = self.value_edit.text().strip()
        if key_text:
            text = f"{key_text} = {val_text}"
        else:
            text = val_text
        dlg = QDialog(self)
        dlg.setWindowTitle("高级编辑 - 原始PDX")
        dlg.setMinimumSize(400, 300)
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        lay = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setPlainText(text)
        lay.addWidget(te)
        btns = QHBoxLayout()
        btns.addStretch()
        ok = QPushButton("确定")
        ok.clicked.connect(dlg.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(dlg.close)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

        def on_advanced_ok():
            """处理高级编辑确认"""
            content = te.toPlainText().strip()
            if "=" in content:
                # 按等号分割，左侧为键名，右侧为值
                parts = content.split("=", 1)
                self.key_edit.setText(parts[0].strip())
                self.value_edit.setText(parts[1].strip())
            else:
                # 没有等号，视为纯值（键名为空）
                self.key_edit.setText("")
                self.value_edit.setText(content)
            dlg.deleteLater()

        dlg.accepted.connect(on_advanced_ok)
        dlg.show()

    def _on_ok(self):
        """确认编辑，生成结果节点

        块节点必须输入键名，值节点允许键名为空（此时直接输出值）。
        根据节点类型创建对应的 TreeNode：
        - 值节点：TreeNode("value", key, value)，key 可为空
        - 块节点：TreeNode("block", key)
        调用 accept() 触发 accepted 信号，关闭对话框。
        """
        key = self.key_edit.text().strip()

        is_block = self.type_block_rb.isChecked()
        if is_block:
            if not key:
                QMessageBox.warning(self, "错误", "块节点键名不能为空")
                return
            self.result_node = TreeNode("block", key)
            # 编辑已有块节点时保留其子节点（对话框只编辑键名/类型），避免清空子内容
            if self.node and self.node.node_type == "block" and self.node.children:
                self.result_node.children = list(self.node.children)
                for child in self.result_node.children:
                    child.parent = self.result_node
        else:
            value = self.value_edit.text().strip()
            self.result_node = TreeNode("value", key, value)
        # 触发生效并关闭对话框
        self.accept()

    def get_node(self) -> TreeNode:
        """获取编辑后生成的结果节点

        在 accepted 信号触发后调用此方法获取用户确认的节点。

        Returns:
            TreeNode: 结果节点，如果对话框被取消则返回 None
        """
        return self.result_node

"""PDX 命令模板选择对话框模块

提供 TemplateDialog 类，用于从 templates 文件夹中读取模板文件，
快速构建国策树节点。支持按类型筛选、关键词搜索。

模板数据来源：
    - templates/ 文件夹（通过 TemplateScheduler 读取）
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QMessageBox, QWidget, QFormLayout
)
from PyQt6.QtCore import Qt
from tree_node import TreeNode, parse_pdx_text_to_nodes
from template_scheduler import get_template_scheduler


CATEGORIES = [
    ("全部", ""),
    ("国策树", "focus_tree"),
    ("单个国策", "focus"),
    ("国家理念", "ideas_file"),
    ("事件", "event"),
    ("决议", "decision"),
    ("法案", "law"),
    ("角色", "character"),
    ("剧本", "bookmark"),
    ("国家历史文件", "country_history"),
    ("脚本化效果/触发器", "scripted"),
    ("界面机制", "gui"),
    ("AI战略编写", "ai_strategy"),
    ("兵种", "unit"),
    ("装备", "equipment"),
    ("科技", "tech"),
    ("关系修正", "opinion_modifier"),
    ("效果器", "effect"),
    ("触发器", "trigger"),
    ("动态修正", "动态修正"),
    ("自定义", "custom"),
]

USAGES = [
    ("全部", ""),
    ("创建文件", "file"),
    ("添加节点", "node"),
]

USAGE_LABELS = {"file": "创建文件", "node": "添加节点", "both": "文件/节点"}


class TemplateDialog(QDialog):
    """PDX 命令模板选择对话框 - 非模态

    从 templates/ 文件夹读取模板文件，用户浏览和选择后插入。
    支持按类型筛选和关键词搜索。

    Attributes:
        scheduler (TemplateScheduler): 模板调度器实例
        result_node (TreeNode): 确认后生成的结果节点
    """

    def __init__(self, scheduler=None, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler or get_template_scheduler()
        self.result_node = None
        self._applied_content = None  # 变量替换后的模板内容（新建文件场景使用）

        self.setWindowTitle("从模板添加")
        self.setMinimumSize(600, 500)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._load_templates()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── 搜索框 ──
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索模板名称...")
        self.search_edit.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # ── 类型筛选 ──
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("类型:"))
        self.category_combo = QComboBox()
        for cn, en in CATEGORIES:
            self.category_combo.addItem(cn, en)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        filter_layout.addWidget(self.category_combo)
        filter_layout.addWidget(QLabel("用途:"))
        self.usage_combo = QComboBox()
        for cn, en in USAGES:
            self.usage_combo.addItem(cn, en)
        self.usage_combo.currentIndexChanged.connect(self._on_category_changed)
        filter_layout.addWidget(self.usage_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # ── 内容区（模板列表 + 预览面板） ──
        content_layout = QHBoxLayout()

        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self._on_item_selected)
        content_layout.addWidget(self.template_list, 1)

        self.preview_widget = QWidget()
        preview_layout = QFormLayout(self.preview_widget)
        self.preview_name_label = QLabel()
        preview_layout.addRow("模板名:", self.preview_name_label)
        self.preview_type_label = QLabel()
        preview_layout.addRow("类型:", self.preview_type_label)
        preview_layout.addRow(QLabel("内容预览:"))
        self.preview_content = QTextEdit()
        self.preview_content.setReadOnly(True)
        self.preview_content.setMaximumHeight(250)
        preview_layout.addRow(self.preview_content)

        content_layout.addWidget(self.preview_widget, 1)
        layout.addLayout(content_layout)

        # ── 底部按钮 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        self._current_template = None

    def _load_templates(self):
        self.template_list.clear()
        category = self.category_combo.currentData()
        usage = self.usage_combo.currentData() or ""
        keyword = self.search_edit.text().strip()

        templates = self.scheduler.search_templates(keyword, category, usage=usage)

        for tmpl in templates:
            usage_label = USAGE_LABELS.get(tmpl.get("usage", ""), "")
            item_text = f"[{tmpl['type_label']}] {tmpl['name']}"
            if usage_label:
                item_text += f"（{usage_label}）"
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, tmpl)
            self.template_list.addItem(list_item)

    def _on_search(self, text):
        self._load_templates()

    def _on_category_changed(self):
        self._load_templates()

    def _on_item_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self._current_template = data
            self.preview_name_label.setText(data["name"])
            self.preview_type_label.setText(data["type_label"])
            content = self.scheduler.get_template_content(data["filepath"])
            self.preview_content.setPlainText(content if content else "")

    def _on_ok(self):
        if not self._current_template:
            QMessageBox.warning(self, "错误", "请从列表中选择一个模板")
            return

        filepath = self._current_template["filepath"]
        content = self.scheduler.get_template_content(filepath)
        if not content:
            QMessageBox.warning(self, "错误", "无法读取模板内容")
            return

        # 直接使用模板内容（变量填写功能已移除）
        self._applied_content = content

        nodes = parse_pdx_text_to_nodes(content.strip())
        if not nodes:
            QMessageBox.warning(self, "错误", "模板内容为空或无法解析")
            return

        if len(nodes) == 1:
            self.result_node = nodes[0]
        else:
            root = TreeNode("block", self._current_template["name"])
            for node in nodes:
                root.add_child(node)
            self.result_node = root

        self.accept()

    def get_node(self) -> TreeNode:
        return self.result_node

    def get_template_data(self) -> dict:
        return self._current_template

    def get_applied_content(self) -> str:
        """获取变量替换后的模板内容（新建文件场景使用）。

        Returns:
            str: 替换后的内容；未选择模板或未确认时为 None
        """
        return self._applied_content

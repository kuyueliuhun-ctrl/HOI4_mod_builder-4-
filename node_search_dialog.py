# -*- coding: utf-8 -*-
"""统一搜索创建对话框模块

提供 NodeSearchDialog 类，合并搜索词条（块/值）与模板，
按词条 node_type 创建块节点或值节点；选中模板时解析为块节点。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QListWidget, QListWidgetItem, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt


class NodeSearchDialog(QDialog):
    """统一搜索创建对话框 - 非模态

    在父块节点下添加新节点时使用：
    - 词条「块」→ 直接创建空块节点 key = { }
    - 词条「值」→ 打开 NodeEditDialog 预填键名，用户输入值后确认
    - 模板 → 解析模板内容为块节点

    Attributes:
        translator (GuiTranslator): 翻译器实例
        result_node (TreeNode): 确认后生成的结果节点
    """

    NODE_TYPE_NAMES = {"block": "块", "value": "值"}

    # 词条块键名 -> 默认节点模板（模板类型, 模板名称关键字）
    # 添加项目时套用全面的默认模板，而不是空块
    DEFAULT_NODE_TEMPLATES = {
        "focus": ("focus", "单个国策"),
        "country_event": ("event", "单个事件"),
        "news_event": ("event", "单个事件"),
        "decision": ("decision", "单个决议"),
        "idea": ("ideas_file", "单个理念"),
        "character": ("character", "单个角色"),
    }

    def __init__(self, translator, parent=None):
        """初始化对话框

        Args:
            translator (GuiTranslator): 翻译器实例（用于词条搜索）
            parent (QWidget): 父窗口
        """
        super().__init__(parent)
        self.translator = translator
        self.result_node = None

        self.setWindowTitle("添加节点（词条 / 模板）")
        self.setMinimumSize(560, 520)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._reload()

    def _setup_ui(self):
        """构建 UI 布局。"""
        layout = QVBoxLayout(self)

        # ── 搜索行 ──
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "搜索词条或模板（中文/英文，如：加政治点数 / random_owned_state）...")
        self.search_edit.textChanged.connect(self._reload)
        search_row.addWidget(self.search_edit, 1)

        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", "")
        self.type_combo.addItem("词条-块", "block")
        self.type_combo.addItem("词条-值", "value")
        self.type_combo.addItem("模板", "template")
        self.type_combo.currentIndexChanged.connect(self._reload)
        search_row.addWidget(self.type_combo)
        layout.addLayout(search_row)

        # ── 结果列表 ──
        layout.addWidget(QLabel("双击选择（词条块→套默认模板；词条值→继续输入值；模板→整块载入）:"))
        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self._on_select)
        self.result_list.itemActivated.connect(self._on_select)
        layout.addWidget(self.result_list, 1)

        # ── 状态栏 + 按钮 ──
        bottom = QHBoxLayout()
        self.status_label = QLabel("")
        bottom.addWidget(self.status_label)
        bottom.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(self.close)
        bottom.addWidget(cancel_btn)
        bottom.addWidget(ok_btn)
        layout.addLayout(bottom)

    def _load_items(self):
        """从词条注册表和模板调度器收集搜索结果。"""
        kw = self.search_edit.text().strip()
        filter_type = self.type_combo.currentData() or ""
        items = []

        # 词条搜索
        if filter_type != "template":
            try:
                from term_registry import get_term_registry
                registry = get_term_registry()
                node_type = filter_type or None
                for term in registry.search(kw, node_type=node_type, limit=500):
                    key = term.get("key", "")
                    cn = term.get("cn", "")
                    ttype = term.get("node_type", "value")
                    tname = self.NODE_TYPE_NAMES.get(ttype, ttype)
                    tags = "、".join(term.get("tags", []))
                    label = f"{key}（{tname}）"
                    if cn and cn != key:
                        label += f" -- {cn}"
                    if tags:
                        label += f" ｜{tags}"
                    items.append({
                        "kind": "term",
                        "label": label,
                        "key": key,
                        "node_type": ttype,
                        "cn": cn,
                    })
            except Exception:
                pass

        # 模板搜索（仅限添加节点用途的模板）
        if filter_type in ("", "template"):
            try:
                from template_scheduler import get_template_scheduler
                scheduler = get_template_scheduler()
                for tpl in scheduler.search_templates(kw, usage="node"):
                    items.append({
                        "kind": "template",
                        "label": f"📄 {tpl['name']}（{tpl['type_label']}）",
                        "key": tpl["name"],
                        "filepath": tpl["filepath"],
                    })
            except Exception:
                pass

        return items

    def _reload(self):
        """刷新结果列表。"""
        self.result_list.clear()
        items = self._load_items()
        for it in items:
            item = QListWidgetItem(it["label"])
            item.setData(Qt.ItemDataRole.UserRole, it)
            self.result_list.addItem(item)
        if items:
            self.status_label.setText(f"共 {len(items)} 条（双击或回车确定）")
        else:
            self.status_label.setText("无匹配结果")

    def _on_select(self, item):
        """处理条目选择，生成结果节点并关闭对话框。"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        self._build_node(data)

    def _build_node(self, data):
        """根据条目数据生成节点。

        词条块 → 空块节点；模板 → 解析为块节点；
        词条值 → 弹出 NodeEditDialog 预填键名。
        """
        from tree_node import TreeNode, tree_from_pdx_text

        if data["kind"] == "template":
            from template_scheduler import get_template_scheduler
            scheduler = get_template_scheduler()
            content = scheduler.get_template_content(data["filepath"]) or ""
            try:
                parsed = tree_from_pdx_text(content)
                if parsed.children:
                    self.result_node = parsed.children[0]
                    self.accept()
                    return
            except Exception:
                pass
            QMessageBox.warning(self, "错误", "模板解析失败，无法创建节点。")
            return

        if data["node_type"] == "block":
            self.result_node = self._default_template_node(data["key"])
            self.accept()
            return

        # 值词条：预填键名打开节点编辑对话框
        from node_edit_dialog import NodeEditDialog
        dlg = NodeEditDialog(self.translator, parent=self,
                             default_type="value", preset_key=data["key"])

        def on_value_ok():
            node = dlg.get_node()
            if node:
                self.result_node = node
                self.accept()
            dlg.deleteLater()

        dlg.accepted.connect(on_value_ok)
        dlg.show()

    @staticmethod
    def _default_template_node(term_key):
        """按词条键名查找默认节点模板，找到则套用模板首个块节点。

        例如添加 focus 块时套用全面的单个国策模板；
        未找到对应模板时返回空块。
        """
        from tree_node import TreeNode, tree_from_pdx_text

        entry = NodeSearchDialog.DEFAULT_NODE_TEMPLATES.get(term_key)
        if entry:
            try:
                from template_scheduler import get_template_scheduler
                scheduler = get_template_scheduler()
                tpl_type, tpl_kw = entry
                matches = scheduler.search_templates(
                    tpl_kw, template_type=tpl_type, usage="node")
                if matches:
                    content = scheduler.get_template_content(
                        matches[0]["filepath"]) or ""
                    parsed = tree_from_pdx_text(content)
                    if parsed.children:
                        return parsed.children[0].clone()
            except Exception:
                pass
        return TreeNode("block", term_key)

    def _on_ok(self):
        """确定按钮：对当前选中项执行与双击相同的操作。"""
        items = self.result_list.selectedItems()
        if not items:
            QMessageBox.information(self, "提示", "请先在列表中选择一个词条或模板。")
            return
        self._on_select(items[0])

    def get_node(self):
        """获取结果节点。

        Returns:
            TreeNode: 用户确认的节点，未选择则返回 None
        """
        return self.result_node

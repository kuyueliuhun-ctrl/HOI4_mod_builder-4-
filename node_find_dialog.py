# -*- coding: utf-8 -*-
"""节点查找定位对话框（Ctrl+F）

在已打开的树编辑器文件中，按英文 id 或中文翻译搜索节点：
- 输入关键词实时列出全部匹配（含路径与中文名）
- 点击结果 / 回车 / F3 定位到树中节点（自动展开祖先并居中）
- F3 下一个，Shift+F3 上一个，Esc 关闭
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton,
)


class NodeFindDialog(QDialog):
    """按英文 id / 中文翻译查找并定位树节点（非模态）。"""

    locate_requested = pyqtSignal(object)   # QModelIndex

    def __init__(self, model, translator=None, parent=None):
        """初始化。

        Args:
            model (FocusTreeModel): 树的 Qt 模型（提供 find_nodes 搜索）
            translator (GuiTranslator, optional): 翻译器（用于中文名显示/搜索）
            parent (QWidget): 父窗口（树编辑器）
        """
        super().__init__(parent)
        self.model = model
        self.translator = translator
        self._results = []      # list[QModelIndex]
        self._cursor = -1

        self.setWindowTitle("查找节点（Ctrl+F）")
        self.resize(580, 440)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._build_ui()

        self._next_shortcut = QShortcut(QKeySequence("F3"), self)
        self._next_shortcut.activated.connect(self._next)
        self._prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        self._prev_shortcut.activated.connect(self._prev)

    def _build_ui(self):
        root = QVBoxLayout(self)

        row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入英文 id 或中文翻译，如 infantry / 步兵…")
        self.search_edit.textChanged.connect(self._reload)
        self.search_edit.returnPressed.connect(self._next)
        row.addWidget(self.search_edit, 1)
        root.addLayout(row)

        self.result_list = QListWidget()
        self.result_list.itemClicked.connect(self._on_item_clicked)
        self.result_list.itemActivated.connect(self._on_item_clicked)
        root.addWidget(self.result_list, 1)

        bottom = QHBoxLayout()
        self.status_label = QLabel("输入关键词开始搜索")
        bottom.addWidget(self.status_label)
        bottom.addStretch()
        self.prev_btn = QPushButton("↑ 上一个（Shift+F3）")
        self.prev_btn.clicked.connect(self._prev)
        self.next_btn = QPushButton("下一个（F3/回车）↓")
        self.next_btn.clicked.connect(self._next)
        bottom.addWidget(self.prev_btn)
        bottom.addWidget(self.next_btn)
        root.addLayout(bottom)

    # ---------- 搜索 ----------

    def _reload(self):
        """按关键词重新搜索并刷新结果列表。"""
        keyword = self.search_edit.text().strip()
        self._results = []
        self._cursor = -1
        self.result_list.clear()
        if not keyword:
            self.status_label.setText("输入关键词开始搜索")
            return
        try:
            self._results = list(self.model.find_nodes(keyword) or [])
        except Exception:
            self._results = []
        if not self._results:
            self.status_label.setText("无匹配结果")
            return
        for idx in self._results:
            item = QListWidgetItem(self._item_text(idx))
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.result_list.addItem(item)
        self._locate(0)

    def _item_text(self, index):
        """构造结果条目文本：节点名 + 中文 + 路径。"""
        node = index.internalPointer()
        if node is None:
            return ""
        key = str(getattr(node, "key", "") or "")
        val = str(getattr(node, "value", "") or "")
        cn = ""
        if self.translator is not None:
            try:
                cn_key, _ = self.translator.translate_node(key, val or None)
                if cn_key and cn_key != key:
                    cn = cn_key
            except Exception:
                pass
        text = f"{key} — {cn}" if cn else key
        if val:
            text += f" = {val}"
        parts = []
        cur = node
        while cur is not None and getattr(cur, "parent", None) is not None:
            parts.append(str(getattr(cur, "key", "") or ""))
            cur = cur.parent
        path = " > ".join(reversed(parts))
        if path:
            text += f"\n{path}"
        return text

    # ---------- 定位 ----------

    def _locate(self, i):
        """定位到第 i 个匹配（循环），并通知编辑器跳转。"""
        if not self._results:
            return
        self._cursor = i % len(self._results)
        idx = self._results[self._cursor]
        self.result_list.setCurrentRow(self._cursor)
        self.locate_requested.emit(idx)
        self.status_label.setText(f"已定位 {self._cursor + 1}/{len(self._results)}")

    def _next(self):
        if self._results:
            self._locate(self._cursor + 1)

    def _prev(self):
        if self._results:
            self._locate(self._cursor - 1)

    def _on_item_clicked(self, item):
        self._locate(self.result_list.row(item))

    # ---------- 外部 ----------

    def focus_search(self):
        """显示并聚焦搜索框。"""
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_edit.setFocus()
        self.search_edit.selectAll()

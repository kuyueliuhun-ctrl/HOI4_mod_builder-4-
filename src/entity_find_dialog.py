# -*- coding: utf-8 -*-
"""实体查找定位对话框（Ctrl+F）

用于实体画廊（国策 / 民族精神 / 角色 / 决议 / 事件等图标型内容）：
- 按英文 id 或中文翻译搜索实体
- 点击结果 / 回车 / F3 定位到画廊中的实体（居中 + 高亮边框）
- F3 下一个，Shift+F3 上一个，Esc 关闭
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton,
)


class EntityFindDialog(QDialog):
    """按英文 id / 中文名搜索实体并发出定位请求（非模态）。"""

    locate_requested = pyqtSignal(str)   # 实体名

    def __init__(self, entities=(), get_cn=None, parent=None):
        """初始化。

        Args:
            entities: 实体名列表
            get_cn:  name -> 中文名 的回调（可空，无则只按英文名搜索）
            parent:  父窗口（FocusView）
        """
        super().__init__(parent)
        self._names = list(entities)
        self._get_cn = get_cn or (lambda name: "")
        self._results = []      # list[str] 匹配的实体名
        self._cursor = -1

        self.setWindowTitle("查找实体（Ctrl+F）")
        self.resize(560, 420)
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
        self.search_edit.setPlaceholderText("输入英文 id 或中文翻译，如 focus / 民族精神…")
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

    def refresh_entities(self, entities):
        """更新实体列表（画廊内容变化后调用）。"""
        self._names = list(entities)
        if self.search_edit.text().strip():
            self._reload()

    # ---------- 搜索 ----------

    def _reload(self):
        """按关键词重新搜索并刷新结果列表。"""
        keyword = self.search_edit.text().strip().lower()
        self._results = []
        self._cursor = -1
        self.result_list.clear()
        if not keyword:
            self.status_label.setText("输入关键词开始搜索")
            return
        for name in self._names:
            cn = (self._get_cn(name) or "")
            if keyword in name.lower() or keyword in cn.lower():
                self._results.append(name)
        if not self._results:
            self.status_label.setText("无匹配结果")
            return
        for name in self._results:
            item = QListWidgetItem(self._item_text(name))
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.result_list.addItem(item)
        self._locate(0)

    def _item_text(self, name):
        """条目文本：中文名（英文 id）。"""
        cn = self._get_cn(name) or ""
        if cn and cn != name:
            return f"{cn}（{name}）"
        return name

    # ---------- 定位 ----------

    def _locate(self, i):
        """定位到第 i 个匹配（循环），并通知画廊跳转。"""
        if not self._results:
            return
        self._cursor = i % len(self._results)
        name = self._results[self._cursor]
        self.result_list.setCurrentRow(self._cursor)
        self.locate_requested.emit(name)
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

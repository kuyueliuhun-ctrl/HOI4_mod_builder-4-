"""图标选择对话框模块

提供 IconPickerDialog，列出游戏与 mod 中的国策图标，支持中英文关键词搜索。
图标来源为 gfx_map（精灵名 -> 纹理路径），由调用方传入（游戏+mod 合并后的映射）。

性能优化：
  - 预先建立排序索引（名称+中文标签），避免每次搜索时重复排序与翻译
  - 搜索输入防抖（150ms），避免每个按键都重建列表
  - 一次性最多显示 MAX_DISPLAY 条，超出部分提示输入关键词筛选
  - 图标异步分批加载（QTimer），界面不卡顿，已加载图标缓存在模块级字典复用
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon

from dds_loader import DdsLoader


# 模块级图标缓存：tex_path -> QPixmap，跨对话框复用，避免重复解码
_ICON_CACHE = {}


class IconPickerDialog(QDialog):
    """图标选择对话框：列出图标并支持中英文搜索（性能优化版）。"""

    MAX_DISPLAY = 300        # 一次最多显示的条目数
    LOAD_BATCH = 12          # 每批异步加载的图标数量
    LOAD_INTERVAL_MS = 40    # 每批加载间隔
    DEBOUNCE_MS = 150        # 搜索防抖间隔

    def __init__(self, gfx_map=None, translator=None, parent=None,
                 prefix="", current_icon=""):
        super().__init__(parent)
        self.gfx_map = gfx_map or {}
        self.translator = translator
        self.selected_name = None
        self.prefix = prefix

        # 预先建立索引：按前缀过滤 + 保留当前图标，一次排序并计算中文标签
        names = [
            name for name in self.gfx_map
            if not prefix or name.startswith(prefix)
        ]
        if current_icon and current_icon in self.gfx_map and current_icon not in names:
            names.append(current_icon)
        self._index = sorted(
            (name, self._build_label(name)) for name in names
        )

        # 搜索防抖定时器
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(self.DEBOUNCE_MS)
        self._search_timer.timeout.connect(self._do_refresh)

        # 图标异步分批加载定时器
        self._load_timer = QTimer(self)
        self._load_timer.setInterval(self.LOAD_INTERVAL_MS)
        self._load_timer.timeout.connect(self._load_next_batch)
        self._pending_items = []  # [(QListWidgetItem, tex_path)]

        self.setWindowTitle("选择图标")
        self.setMinimumSize(500, 520)

        self._setup_ui()
        self.finished.connect(self._on_finished)
        self._do_refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入图标名或中文（支持中英文搜索）...")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # 前缀过滤提示
        if self.prefix:
            filter_label = QLabel(f"仅显示以 <code>{self.prefix}</code> 开头的图标")
            filter_label.setStyleSheet("color: #ff9800; font-size: 11px;")
            layout.addWidget(filter_label)

        # 计数提示
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.count_label)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.setSpacing(2)
        self.list_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.list_widget.itemDoubleClicked.connect(self._accept_current)
        layout.addWidget(self.list_widget, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _build_label(self, name: str) -> str:
        """生成图标显示文本：图标名（中文名，若有）"""
        base = name[4:] if name.startswith("GFX_") else name
        cn = ""
        if self.translator:
            translated = self.translator.translate_key(base)
            if translated and translated != base:
                cn = translated
        if cn:
            return f"{name}（{cn}）"
        return name

    def _on_search_text_changed(self, text):
        # 防抖：等待输入停顿后再重建列表
        self._search_timer.start()

    def _do_refresh(self):
        keyword = self.search_edit.text()
        self._load_timer.stop()
        self._pending_items.clear()
        self.list_widget.clear()

        kw = keyword.strip().lower()
        if kw:
            # 直接过滤预先建立的索引，避免重复排序
            matched = [
                (name, label) for name, label in self._index
                if kw in name.lower() or kw in label.lower()
            ]
        else:
            matched = self._index

        total = len(matched)
        shown = matched[:self.MAX_DISPLAY]

        for name, label in shown:
            item = QListWidgetItem(label)
            tex_path = self.gfx_map.get(name)
            pm = _ICON_CACHE.get(tex_path) if tex_path else None
            if pm is not None:
                item.setIcon(QIcon(pm))
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)
            # 尚未缓存的图标加入异步加载队列
            if tex_path and pm is None:
                self._pending_items.append((item, tex_path))

        self._update_count(total)

        if self._pending_items:
            self._load_timer.start()

    def _load_next_batch(self):
        """异步分批加载图标，避免一次性解码大量 DDS 造成卡顿。"""
        batch = self._pending_items[:self.LOAD_BATCH]
        del self._pending_items[:self.LOAD_BATCH]
        if not batch:
            self._load_timer.stop()
            return
        for item, tex_path in batch:
            pm = _ICON_CACHE.get(tex_path)
            if pm is None:
                pm = DdsLoader.load_as_pixmap(tex_path)
                if pm is not None:
                    _ICON_CACHE[tex_path] = pm
            if pm is not None:
                try:
                    item.setIcon(QIcon(pm))
                except RuntimeError:
                    pass  # 条目已随搜索刷新销毁
        if not self._pending_items:
            self._load_timer.stop()

    def _update_count(self, total):
        if total > self.MAX_DISPLAY:
            self.count_label.setText(f"共 {total} 个图标，显示前 {self.MAX_DISPLAY} 个，请输入关键词筛选")
        else:
            self.count_label.setText(f"共 {total} 个图标")

    def _on_finished(self, *args):
        # 对话框关闭时停止异步加载
        self._load_timer.stop()
        self._search_timer.stop()

    def _current_icon_name(self):
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _accept_current(self, item=None):
        name = self._current_icon_name()
        if name:
            self.selected_name = name
            self.accept()

    def _on_ok(self):
        self._accept_current()

    def get_selected_icon(self) -> str:
        """返回选中的精灵名，取消则返回 None"""
        return self.selected_name

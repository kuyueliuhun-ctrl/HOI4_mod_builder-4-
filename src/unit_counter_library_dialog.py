"""单位标牌库对话框（SF 移植：unit_counter_libraries 浏览）

浏览从游戏本体提取的单位标牌图标库（onmap_* 各军种兵牌），
支持类别过滤/搜索；库缺失时一键从游戏导入；双击复制文件路径。
"""

import os

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QMessageBox,
)
from PyQt6.QtGui import QPixmap, QIcon


class UnitCounterLibraryDialog(QDialog):
    """单位标牌库浏览/导入。"""

    def __init__(self, game_path="", lib_dir=None, parent=None):
        super().__init__(parent)
        self.game_path = game_path
        self.lib = None
        from unit_counter_library import UnitCounterLibrary
        self.lib = UnitCounterLibrary(lib_dir)
        self.setWindowTitle("单位标牌库（HOI4 地图兵牌）")
        self.resize(820, 560)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.import_btn = QPushButton("⬇ 从游戏导入")
        self.import_btn.clicked.connect(self._import)
        bar.addWidget(self.import_btn)
        bar.addWidget(QLabel("类别:"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("全部", "")
        self.cat_combo.currentIndexChanged.connect(self._refresh)
        bar.addWidget(self.cat_combo)
        bar.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("名称，如 onmap_infantry")
        self.search_edit.textChanged.connect(self._refresh)
        bar.addWidget(self.search_edit, 1)
        root.addLayout(bar)

        self.status_label = QLabel("")
        root.addWidget(self.status_label)

        self.list_widget = QListWidget(self)
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setGridSize(QSize(140, 88))
        self.list_widget.itemDoubleClicked.connect(self._copy_path)
        root.addWidget(self.list_widget, 1)

        self.hint_label = QLabel("双击图标复制文件路径到剪贴板")
        root.addWidget(self.hint_label)

    def _import(self):
        if not self.game_path or not os.path.isdir(self.game_path):
            QMessageBox.information(
                self, "提示",
                "未配置游戏目录（工具菜单 → 配置向导…设置 HOI4 路径）。")
            return
        try:
            from unit_counter_library import import_unit_counter_library
            import time
            t0 = time.time()
            r = import_unit_counter_library(self.game_path)
            QMessageBox.information(
                self, "导入完成",
                f"已导入 {r['total']} 个标牌到:\n{r['out_dir']}\n"
                f"耗时 {time.time() - t0:.1f}s")
            from unit_counter_library import UnitCounterLibrary
            self.lib = UnitCounterLibrary()
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _refresh(self):
        if self.lib is None:
            return
        if not self.lib.is_ready:
            self.status_label.setText(
                "标牌库为空——点击「⬇ 从游戏导入」从游戏本体提取")
            self.list_widget.clear()
            self.cat_combo.clear()
            self.cat_combo.addItem("全部", "")
            return
        # 类别下拉
        cur = self.cat_combo.currentData() or ""
        self.cat_combo.blockSignals(True)
        self.cat_combo.clear()
        self.cat_combo.addItem("全部", "")
        for cat in self.lib.categories:
            self.cat_combo.addItem(cat, cat)
        idx = self.cat_combo.findData(cur)
        self.cat_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.cat_combo.blockSignals(False)

        kw = self.search_edit.text().strip()
        cat = self.cat_combo.currentData() or ""
        self.list_widget.clear()
        for e in self.lib.search(kw):
            if cat and e.get("category") != cat:
                continue
            abs_p = self.lib.abs_path(e)
            pm = QPixmap(abs_p)
            if pm.isNull():
                continue
            icon = QIcon(pm)
            item = QListWidgetItem(icon, e["name"])
            item.setToolTip(
                f"{e['name']}\n{e['category']}  {e['size']}\n{abs_p}")
            item.setData(Qt.ItemDataRole.UserRole, abs_p)
            self.list_widget.addItem(item)
        self.status_label.setText(
            f"共 {self.lib.names.__len__()} 个标牌，显示 "
            f"{self.list_widget.count()} 个")

    def _copy_path(self, item):
        path = item.data(Qt.ItemDataRole.UserRole) or ""
        if path:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(path)
            self.hint_label.setText(f"已复制: {path}")

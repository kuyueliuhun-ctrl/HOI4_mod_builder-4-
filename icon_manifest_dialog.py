"""图标库 manifest 对话框（SF 移植：图标库 manifest 结构）

展示 mod+游戏全部 gfx spriteType 的图标清单（名称/贴图/来源/尺寸/
贴图存在性），支持搜索过滤与 JSON 导出；清单可供外置 Agent（API/MCP）
与导出前检查复用。
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog, QComboBox,
)

_SOURCE_CN = {"mod": "mod", "vanilla": "游戏"}


class IconManifestDialog(QDialog):
    """图标库 manifest 浏览/导出。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self.entries = []
        self.stats = None
        self.setWindowTitle("图标库 manifest（mod + 游戏全部 gfx sprite）")
        self.resize(960, 620)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.summary_label = QLabel("构建中…")
        root.addWidget(self.summary_label)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("sprite 名子串，如 GFX_focus_GER")
        self.search_edit.textChanged.connect(self._refresh)
        bar.addWidget(self.search_edit, 1)
        bar.addWidget(QLabel("来源:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("全部", "")
        self.source_combo.addItem("mod", "mod")
        self.source_combo.addItem("游戏", "vanilla")
        self.source_combo.currentIndexChanged.connect(self._refresh)
        bar.addWidget(self.source_combo)
        self.export_btn = QPushButton("💾 导出 JSON")
        self.export_btn.clicked.connect(self._export)
        bar.addWidget(self.export_btn)
        root.addLayout(bar)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(
            ["sprite 名", "贴图路径", "来源", "尺寸", "md5", "状态"])
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(1, 360)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(5, 70)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, 1)

    def _load(self):
        try:
            from icon_manifest import build_icon_manifest
            m = build_icon_manifest(self.mod_path, self.hoi4_path)
            self.entries = m["entries"]
            self.stats = m["stats"]
        except Exception as e:
            QMessageBox.critical(self, "构建失败", str(e))
            self.entries = []
            self.stats = None
            return
        self.summary_label.setText(
            f"共 {self.stats['total']} 个 sprite | 缺贴图 "
            f"{self.stats['missing']} | 来源 {self.stats['sources']}")
        self._refresh()

    def _refresh(self):
        kw = self.search_edit.text().strip()
        src = self.source_combo.currentData() or ""
        self.table.setRowCount(0)
        shown = 0
        for e in self.entries:
            if kw and kw not in e["name"]:
                continue
            if src and e.get("source") != src:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(e["name"]))
            self.table.setItem(r, 1, QTableWidgetItem(e.get("texture", "")))
            self.table.setItem(r, 2, QTableWidgetItem(
                _SOURCE_CN.get(e.get("source", ""), e.get("source", ""))))
            size = e.get("size")
            self.table.setItem(r, 3, QTableWidgetItem(
                "%dx%d" % (size[0], size[1]) if size else ""))
            self.table.setItem(r, 4, QTableWidgetItem(e.get("md5") or ""))
            self.table.setItem(r, 5, QTableWidgetItem(
                "缺贴图" if e.get("missing") else "正常"))
            shown += 1
            if shown >= 2000:
                break
        self.summary_label.setText(
            self.summary_label.text().split("｜")[0]
            + f"｜ 当前显示 {shown} 条")

    def _export(self):
        default = os.path.join(self.mod_path or os.getcwd(),
                               "icon_manifest.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出图标清单", default, "JSON (*.json)")
        if not path:
            return
        try:
            from icon_manifest import write_icon_manifest
            write_icon_manifest(self.mod_path, self.hoi4_path, path)
            QMessageBox.information(self, "已导出", f"已导出到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

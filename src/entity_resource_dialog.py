"""实体配套资源工作台对话框

按文件 / 国家 / 整个 Mod 列出所有可本地化、可上传图标的实体，
支持：
  - 表格内直接编辑中文/英文本地化
  - 保存本地化（只写 mod）
  - 为选中行指定/上传图标
  - 一键补全缺失光效 GFX（已有不改；提供“打开时自动补全”选项）
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from entity_resource_data import (
    collect_resource_items,
    ensure_shine_gfx,
    save_loc_edits,
)

# 表格列布局
COL_TYPE = 0
COL_KEY = 1
COL_FILE = 2
COL_ICON = 3
COL_ICON_FILE = 4
COL_GFX = 5
COL_SHINE = 6
COL_CN_NAME = 7
COL_CN_DESC = 8
COL_EN_NAME = 9
COL_EN_DESC = 10

_COL_NAMES = [
    "类型", "实体", "文件", "图标", "图标文件", "普通GFX", "光效GFX",
    "中文名", "中文描述", "英文名", "英文描述",
]

_EDITABLE_COLS = {COL_CN_NAME, COL_CN_DESC, COL_EN_NAME, COL_EN_DESC}


class EntityResourceDialog(QDialog):
    """实体配套资源工作台（非模态）。"""

    def __init__(self, mod_path="", hoi4_path="",
                 initial_file="", initial_country="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.initial_file = initial_file or ""
        self.initial_country = initial_country or ""
        self._items = []
        self._items_by_row = {}
        self._changed = set()

        self.setWindowTitle("实体配套资源工作台")
        self.resize(1200, 720)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._build_ui()
        self._refresh()

    # ---------- UI ----------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 范围行
        scope = QHBoxLayout()
        scope.addWidget(QLabel("范围:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("整个 Mod", "mod")
        self.scope_combo.addItem("指定文件…", "file")
        self.scope_combo.addItem("指定国家…", "country")
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        scope.addWidget(self.scope_combo)

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("相对 mod 路径，如 common/national_focus/xxx.txt")
        self.file_edit.setMinimumWidth(360)
        scope.addWidget(self.file_edit, 1)

        self.browse_btn = QPushButton("浏览…")
        self.browse_btn.clicked.connect(self._browse_file)
        scope.addWidget(self.browse_btn)

        self.country_edit = QLineEdit()
        self.country_edit.setPlaceholderText("国家 TAG，如 GER")
        self.country_edit.setFixedWidth(90)
        scope.addWidget(self.country_edit)

        self.refresh_btn = QPushButton("⟳ 刷新")
        self.refresh_btn.clicked.connect(self._refresh)
        scope.addWidget(self.refresh_btn)
        layout.addLayout(scope)

        # 操作行
        ops = QHBoxLayout()
        self.auto_shine_check = QCheckBox("刷新/上传后自动补全缺失光效")
        self.auto_shine_check.setToolTip("只补缺失，已有光效不会修改")
        ops.addWidget(self.auto_shine_check)

        fill_btn = QPushButton("✨ 补全缺失光效")
        fill_btn.clicked.connect(self._on_fill_shine)
        ops.addWidget(fill_btn)

        save_btn = QPushButton("💾 保存本地化")
        save_btn.clicked.connect(self._on_save_loc)
        ops.addWidget(save_btn)

        upload_btn = QPushButton("🖼 上传图标（选中行）")
        upload_btn.clicked.connect(self._on_upload_icon)
        ops.addWidget(upload_btn)

        ops.addStretch()
        layout.addLayout(ops)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(_COL_NAMES))
        self.table.setHorizontalHeaderLabels(_COL_NAMES)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            COL_KEY, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            COL_FILE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table, 1)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ---------- 范围 ----------
    def _on_scope_changed(self):
        scope = self.scope_combo.currentData()
        is_file = scope == "file"
        self.file_edit.setVisible(is_file)
        self.browse_btn.setVisible(is_file)
        self.country_edit.setVisible(scope == "country")

    def _browse_file(self):
        start = self.mod_path or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择脚本文件", start, "PDX 脚本 (*.txt);;所有文件 (*)")
        if path and self.mod_path:
            rel = os.path.relpath(path, self.mod_path).replace("\\", "/")
            self.file_edit.setText(rel)

    def _current_scope(self):
        scope = self.scope_combo.currentData()
        if scope == "file":
            return {"filepath": self.file_edit.text().strip() or None,
                    "country": None}
        if scope == "country":
            return {"filepath": None,
                    "country": self.country_edit.text().strip().upper() or None}
        return {"filepath": None, "country": None}

    # ---------- 数据 ----------
    def _refresh(self):
        if not self.mod_path:
            return
        scope = self._current_scope()
        self._items = collect_resource_items(
            self.mod_path, self.hoi4_path,
            filepath=scope["filepath"], country=scope["country"])
        self._items_by_row = {}
        self._changed = set()
        self.table.setRowCount(0)

        for i, item in enumerate(self._items):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._items_by_row[row] = item

            values = [
                item["type"], item["key"], item["file"], item["icon"],
                "有" if item["icon_file_exists"] else ("无" if item["icon"] else ""),
                "已注册" if item["icon_registered"] else ("缺失" if item["icon"] else ""),
                "已注册" if item["shine_registered"] else ("缺失" if item["icon"] and item["icon_registered"] else ""),
                item["translations"]["simp_chinese"].get(item["loc_keys"][0] if item["loc_keys"] else item["key"], ""),
                item["translations"]["simp_chinese"].get((item["key"] + "_desc") if item["key"] else "", ""),
                item["translations"]["english"].get(item["loc_keys"][0] if item["loc_keys"] else item["key"], ""),
                item["translations"]["english"].get((item["key"] + "_desc") if item["key"] else "", ""),
            ]
            for col, val in enumerate(values):
                item_widget = QTableWidgetItem(str(val))
                item_widget.setData(Qt.ItemDataRole.UserRole, val)
                if col in _EDITABLE_COLS:
                    item_widget.setFlags(item_widget.flags() | Qt.ItemFlag.ItemIsEditable)
                    item_widget.setText(str(val))
                else:
                    item_widget.setFlags(item_widget.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item_widget)

        self.status_label.setText(
            "共 {} 条实体（缺失光效 {} 条，缺失本地化键 {} 条）".format(
                len(self._items),
                sum(1 for it in self._items if it["icon"] and it["icon_registered"] and not it["shine_registered"]),
                sum(1 for it in self._items
                    for lang in ("simp_chinese",)
                    for k in it["loc_keys"]
                    if not it["translations"][lang].get(k))))

    # ---------- 操作 ----------
    def _on_fill_shine(self):
        done = 0
        skipped = 0
        for item in self._items:
            if not item["icon"] or not item["icon_registered"] or item["shine_registered"]:
                continue
            if ensure_shine_gfx(self.mod_path, item["icon"], item["icon_texture"]):
                done += 1
            else:
                skipped += 1
        QMessageBox.information(
            self, "补全光效",
            "已补全 {} 条缺失光效；跳过/已有 {} 条。".format(done, skipped))
        if done:
            self._refresh()

    def _on_save_loc(self):
        edits = []
        for row, item in self._items_by_row.items():
            for col, lang, key_suffix in (
                    (COL_CN_NAME, "simp_chinese", 0),
                    (COL_CN_DESC, "simp_chinese", 1),
                    (COL_EN_NAME, "english", 0),
                    (COL_EN_DESC, "english", 1)):
                val = self.table.item(row, col).text().strip()
                orig = self.table.item(row, col).data(Qt.ItemDataRole.UserRole)
                if val == orig:
                    continue
                if key_suffix == 1:
                    key = (item["key"] + "_desc") if item["key"] else ""
                else:
                    key = item["loc_keys"][0] if item["loc_keys"] else item["key"]
                if key:
                    edits.append({"key": key, "value": val, "lang": lang})
        if not edits:
            QMessageBox.information(self, "保存本地化", "没有修改内容。")
            return
        written = save_loc_edits(self.mod_path, edits)
        QMessageBox.information(
            self, "保存本地化",
            "已保存 {} 条修改到 mod。".format(written))
        self._refresh()

    def _on_upload_icon(self):
        row = self.table.currentRow()
        if row < 0 or row not in self._items_by_row:
            QMessageBox.information(self, "提示", "请先选择一个实体。")
            return
        item = self._items_by_row[row]
        from content_types import ICON_RULES
        cfg = ICON_RULES.get(item["type"], {}).get("upload")
        if not cfg:
            QMessageBox.information(self, "提示", "该类型暂不支持图标上传（{}）。".format(item["type"]))
            return
        start = self.mod_path or ""
        image_path, _ = QFileDialog.getOpenFileName(
            self, "选择图标图片", start, "图片 (*.png *.jpg *.jpeg *.dds *.tga)")
        if not image_path:
            return
        from icon_ops import upload_icon
        try:
            icon_name = upload_icon(self.mod_path, image_path, item["key"], cfg)
        except Exception as e:
            QMessageBox.warning(self, "上传失败", str(e))
            return
        QMessageBox.information(self, "上传图标", "已上传，图标名：{}".format(icon_name))
        if self.auto_shine_check.isChecked():
            self._on_fill_shine()
        else:
            self._refresh()


def open_entity_resource_dialog(mod_path="", hoi4_path="",
                                initial_file="", initial_country="", parent=None):
    """工厂函数：打开实体配套资源工作台。"""
    dlg = EntityResourceDialog(
        mod_path=mod_path, hoi4_path=hoi4_path,
        initial_file=initial_file, initial_country=initial_country,
        parent=parent)
    dlg.show()
    return dlg
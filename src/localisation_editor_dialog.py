"""本地化编辑器对话框（UI 层 + 少量信号槽编排）

套用现有“词条管理（TermDialog）”的表格风格：
  - 顶部筛选：语言 / 搜索 / 来源 / 只看修正
  - 默认简体中文；仅当用户选择 English 时才显示英文并与中文对照
  - 表格展示：键 / 当前语言值 / 对照值（英文模式）/ 来源 / 所在文件
  - 支持新增、编辑、删除、刷新、批量补写缺失词条
  - 写入只落到 mod 本地化文件，不修改游戏原始文件
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QCheckBox,
)

from localisation_editor_data import (
    LANG_LABELS,
    LOC_CATEGORIES,
    batch_fill_missing_loc,
    build_entries,
    categorise_key,
    default_mod_loc_file,
    delete_loc_entry,
    is_modifier_key,
    list_loc_files,
    load_effective_dict,
    upsert_loc_entry,
)

LANG_LABELS = {
    "simp_chinese": "简体中文",
    "english": "English",
}


class LocalisationEditorDialog(QDialog):
    """本地化编辑器对话框（非模态，仿 TermDialog 布局）。"""

    def __init__(self, mod_path: str, hoi4_path: str = "",
                 lang: str = "simp_chinese", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path
        self.hoi4_path = hoi4_path
        self.lang = lang
        self._all_entries = []

        self.setWindowTitle("本地化编辑器（mod 文件）")
        self.setMinimumSize(900, 600)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._setup_ui()
        self._reload_files()
        self._reload()

    # ───────────────────────── UI ─────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 筛选行
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("语言:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(LANG_LABELS["simp_chinese"], "simp_chinese")
        self.lang_combo.addItem(LANG_LABELS["english"], "english")
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        filter_row.addWidget(self.lang_combo)

        filter_row.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("键 / 当前值 / 对照值")
        self.search_edit.textChanged.connect(self._reload)
        filter_row.addWidget(self.search_edit, 1)

        filter_row.addWidget(QLabel("来源:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("全部", "")
        self.source_combo.addItem("仅 mod", "mod")
        self.source_combo.addItem("仅游戏", "game")
        self.source_combo.currentIndexChanged.connect(self._reload)
        filter_row.addWidget(self.source_combo)

        filter_row.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        for cat in LOC_CATEGORIES:
            self.category_combo.addItem(cat, cat if cat != "全部" else "")
        self.category_combo.currentIndexChanged.connect(self._reload)
        filter_row.addWidget(self.category_combo)

        self.modifier_check = QCheckBox("只看修正词条")
        self.modifier_check.toggled.connect(self._reload)
        filter_row.addWidget(self.modifier_check)
        layout.addLayout(filter_row)

        # 写入目标文件行（新增/游戏词条转写时使用）
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("写入文件:"))
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(400)
        target_row.addWidget(self.target_combo, 1)
        self.target_hint = QLabel("（游戏词条编辑/新增时写入所选 mod 文件）")
        self.target_hint.setStyleSheet("color: gray;")
        target_row.addWidget(self.target_hint)
        layout.addLayout(target_row)

        # 操作按钮
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 新增词条")
        add_btn.clicked.connect(self._on_add)
        edit_btn = QPushButton("✎ 编辑选中")
        edit_btn.clicked.connect(self._on_edit)
        del_btn = QPushButton("🗑 删除选中")
        del_btn.clicked.connect(self._on_delete)
        fill_btn = QPushButton("🔍 补写缺失词条")
        fill_btn.clicked.connect(self._on_batch_fill)
        refresh_btn = QPushButton("⟳ 刷新")
        refresh_btn.clicked.connect(self._reload_all)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addWidget(fill_btn)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["键", "中文值", "游戏原文", "来源", "所在mod文件"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(lambda *_: self._on_edit())
        layout.addWidget(self.table)

        # 状态
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # 关闭
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ───────────────────────── 语言切换 ─────────────────────────

    def _on_lang_changed(self):
        lang = self.lang_combo.currentData() or "simp_chinese"
        self.lang = lang
        self._update_table_headers()
        self._reload_files()
        self._reload()

    def _update_table_headers(self):
        if self.lang == "english":
            self.table.setHorizontalHeaderLabels(
                ["键", "英文值", "中文参考", "来源", "所在mod文件"])
        else:
            self.table.setHorizontalHeaderLabels(
                ["键", "中文值", "游戏原文", "来源", "所在mod文件"])

    # ───────────────────────── 数据加载 ─────────────────────────

    def _reload_files(self):
        """刷新写入文件下拉列表。"""
        self.target_combo.clear()
        files = list_loc_files(self.mod_path, self.lang)
        for fp in files:
            rel = _pretty_path(fp, self.mod_path)
            self.target_combo.addItem(rel, fp)
        if not files:
            default = default_mod_loc_file(self.mod_path, self.lang)
            self.target_combo.addItem(
                "默认（{}）".format(os.path.basename(default)), default)

    def _reload_all(self):
        self._reload_files()
        self._reload()

    def _reload(self):
        kw = self.search_edit.text().strip().lower()
        source = self.source_combo.currentData() or None
        category = self.category_combo.currentData() or None
        modifier_only = self.modifier_check.isChecked()

        entries = build_entries(self.mod_path, self.hoi4_path, self.lang)
        # 英文模式额外加载中文参考
        if self.lang == "english":
            chinese = load_effective_dict(self.mod_path, self.hoi4_path, "simp_chinese")
            for e in entries:
                e["alt_value"] = chinese.get(e["key"], "")
        else:
            for e in entries:
                e["alt_value"] = ""

        filtered = []
        for e in entries:
            if source and e["source"] != source:
                continue
            if modifier_only and not is_modifier_key(e["key"]):
                continue
            if category and categorise_key(e["key"]) != category:
                continue
            if kw:
                haystack = " ".join([
                    e["key"].lower(),
                    e["value"].lower(),
                    e.get("alt_value", "").lower(),
                    e.get("game_value", "").lower(),
                ])
                if kw not in haystack:
                    continue
            filtered.append(e)

        self._all_entries = filtered
        self.table.setRowCount(0)
        for e in filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(e["key"]))
            self.table.setItem(row, 1, QTableWidgetItem(e["value"]))
            # 第二列之后动态显示：英文模式显示中文参考，中文模式显示游戏原文
            if self.lang == "english":
                self.table.setItem(row, 2, QTableWidgetItem(e.get("alt_value", "")))
            else:
                self.table.setItem(row, 2, QTableWidgetItem(e.get("game_value", "")))
            self.table.setItem(row, 3, QTableWidgetItem(
                "mod" if e["source"] == "mod" else "游戏"))
            self.table.setItem(row, 4, QTableWidgetItem(
                os.path.basename(e["file"]) if e["file"] else ""))
            for col in range(5):
                item = self.table.item(row, col)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, e)

        self.status_label.setText("共 {} 条".format(len(filtered)))

    # ───────────────────────── 操作 ─────────────────────────

    def _selected_entry(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _target_filepath(self):
        data = self.target_combo.currentData()
        if data:
            return data
        return default_mod_loc_file(self.mod_path, self.lang)

    def _on_add(self):
        dlg = _EntryEditDialog(None, lang=self.lang, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            target = self._target_filepath()
            ok = upsert_loc_entry(target, data["key"], data["value"], self.lang)
            if ok:
                self._reload_all()
            else:
                QMessageBox.warning(self, "错误", "写入失败，请检查路径与文件权限。")

    def _on_edit(self):
        e = self._selected_entry()
        if not e:
            QMessageBox.information(self, "提示", "请先选择一个词条")
            return
        target = e["file"] or self._target_filepath()
        dlg = _EntryEditDialog(e, lang=self.lang, target=target, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ok = upsert_loc_entry(target, data["key"], data["value"], self.lang)
            if ok:
                if e["source"] == "mod" and data["key"] != e["key"]:
                    # 重命名键：删除旧键
                    delete_loc_entry(e["file"], e["key"], self.lang)
                self._reload_all()
            else:
                QMessageBox.warning(self, "错误", "写入失败，请检查路径与文件权限。")

    def _on_delete(self):
        e = self._selected_entry()
        if not e:
            QMessageBox.information(self, "提示", "请先选择一个词条")
            return
        if e["source"] == "game" and not e["file"]:
            QMessageBox.information(
                self, "提示",
                "该词条只存在于游戏原始文件，不能删除。\n"
                "如需覆盖，请编辑后写入 mod 文件。")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除词条 '{}' 吗？\n仅从 mod 文件删除，游戏词条不受影响。".format(e["key"]))
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok = delete_loc_entry(e["file"], e["key"], self.lang)
        if ok:
            self._reload_all()

    def _on_batch_fill(self):
        """批量补写当前语言缺失的本地化词条。"""
        target = self._target_filepath()
        written, target_path = batch_fill_missing_loc(
            self.mod_path, self.hoi4_path, self.lang, target_file=target)
        if written:
            QMessageBox.information(
                self, "补写完成",
                "已补写 {} 条缺失词条到：\n{}".format(written, target_path))
        else:
            QMessageBox.information(
                self, "补写完成",
                "未发现缺失词条，或目标文件已包含对应键。")
        self._reload_all()


class _EntryEditDialog(QDialog):
    """新增/编辑本地化词条对话框。"""

    def __init__(self, entry=None, lang: str = "simp_chinese",
                 target: str = "", parent=None):
        super().__init__(parent)
        self.entry = entry
        self.lang = lang
        self.setWindowTitle("编辑词条" if entry else "新增词条")
        self.setMinimumSize(540, 180)

        value_label = "英文:" if lang == "english" else "中文:"

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("本地化键，如 focus_xxx / MODIFIER_xxx")
        if entry:
            self.key_edit.setText(entry["key"])
        form.addRow("键:", self.key_edit)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText(value_label + "翻译文本")
        if entry:
            self.value_edit.setText(entry["value"])
        form.addRow(value_label, self.value_edit)

        if target:
            tip = QLabel("写入文件：{}".format(os.path.basename(target)))
            tip.setStyleSheet("color: gray;")
            form.addRow("目标:", tip)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _on_ok(self):
        if not self.key_edit.text().strip():
            QMessageBox.warning(self, "错误", "键不能为空")
            return
        self.accept()

    def get_data(self):
        return {
            "key": self.key_edit.text().strip(),
            "value": self.value_edit.text().strip(),
        }


def _pretty_path(path: str, mod_path: str) -> str:
    """显示相对 mod 根目录的路径，便于用户辨认。"""
    try:
        return os.path.relpath(path, mod_path)
    except ValueError:
        return path
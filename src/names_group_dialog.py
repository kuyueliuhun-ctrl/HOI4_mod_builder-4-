# -*- coding: utf-8 -*-
"""OOB 命名组（division_names_group）编辑器对话框。

左侧组列表；右侧表单编辑 icon/order/is_name/generic/name；
「名称条目（name = {…}）结构化块」由独立小对话框编辑；
保存时写回 OOB 文件（原子写 + ensure_file_in_mod，块级保留未编辑项）。
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QVBoxLayout, QWidget,
)

from ai_ui_common import EntityListSidebar
from oob_loader import load_names_groups, save_names_group
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text


def _parse_name_entries(raw_block):
    """解析 name = {…} 块文本 → [{"key", "raw", "flags"}]。"""
    if not raw_block:
        return []
    from tree_node import parse_pdx_text_to_nodes
    entries = []
    try:
        nodes = parse_pdx_text_to_nodes(raw_block)
        if nodes and nodes[0].node_type == "block":
            for c in nodes[0].children:
                if c.node_type != "block":
                    continue
                flags = {}
                for sub in c.children:
                    if sub.node_type == "value":
                        flags[sub.key] = sub.value
                entries.append({
                    "key": c.key,
                    "raw": c.to_pdx(1),
                    "flags": flags,
                })
    except Exception:
        pass
    return entries


def _render_name_entries(entries):
    """序列化 name = {…} 块文本。"""
    lines = ["name = {"]
    for e in entries or []:
        raw = e.get("raw") if isinstance(e, dict) else ""
        if not raw:
            key = e if isinstance(e, str) else e.get("key", "")
            raw = '\t"%s" = { }' % key.replace('"', '')
        for ln in raw.splitlines():
            lines.append("\t" + ln if ln.strip() else "")
    lines.append("}")
    return "\n".join(lines)


class NameEntriesDialog(QDialog):
    """名称序列结构化块编辑（name = {…} 的子条目）。"""

    def __init__(self, entries=None, parent=None):
        super().__init__(parent)
        self.entries = list(entries or [])
        self.setWindowTitle("名称序列（结构化块）")
        self.resize(680, 440)
        root = QVBoxLayout(self)
        tip = QLabel("每个名称条目为 name = {…} 下的子块；原始子块文本保留，"
                     "已识别的 is_name/generic 标记展示为字段。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#5d6b7a; font-size:11px;")
        root.addWidget(tip)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["名称（键）", "is_name", "原始子块"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        btns = QHBoxLayout()
        add_btn = QPushButton("＋ 添加")
        add_btn.clicked.connect(self._add_row)
        del_btn = QPushButton("－ 删除选中")
        del_btn.clicked.connect(self._remove_selected)
        save_btn = QPushButton("💾 应用")
        save_btn.clicked.connect(self._apply)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        root.addLayout(btns)

        for e in self.entries:
            self._append_row(e)

    def _append_row(self, e):
        r = self.table.rowCount()
        self.table.insertRow(r)
        flags = e.get("flags") or {}
        self.table.setItem(r, 0, QTableWidgetItem(e.get("key", "")))
        self.table.setItem(r, 1, QTableWidgetItem(str(flags.get("is_name", ""))))
        self.table.setItem(r, 2, QTableWidgetItem(e.get("raw", "")))

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c in range(3):
            self.table.setItem(r, c, QTableWidgetItem(""))

    def _remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _apply(self):
        entries = []
        for r in range(self.table.rowCount()):
            key_item = self.table.item(r, 0)
            raw_item = self.table.item(r, 2)
            key = key_item.text().strip() if key_item else ""
            raw = raw_item.text() if raw_item else ""
            if not key and not raw:
                continue
            if raw:
                entries.append({"key": key, "raw": raw, "flags": {}})
            else:
                entries.append({"key": key, "raw": '\t"%s" = { }' % key,
                                "flags": {}})
        self.entries = entries
        self.accept()


class NamesGroupDialog(QDialog):
    """OOB 命名组编辑器（非模态）。"""

    def __init__(self, file_path="", mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.file_path = file_path or ""
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.groups = {}
        self.current_id = ""
        self._name_entries = None
        self._name_entries_edited = False

        self.setWindowTitle("OOB 命名组编辑器")
        self.resize(920, 620)
        root = QHBoxLayout(self)

        self.sidebar = EntityListSidebar(
            "命名组", parent=self, enable_crud=False,
            mod_path=self.mod_path, hoi4_path=self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_select)
        root.addWidget(self.sidebar)

        right = QWidget()
        form_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)
        self.icon_edit = QLineEdit()
        self.order_edit = QLineEdit()
        self.is_name_combo = QComboBox()
        self.is_name_combo.addItems(["", "yes", "no"])
        self.generic_combo = QComboBox()
        self.generic_combo.addItems(["", "yes", "no"])
        self.name_edit = QLineEdit()
        self.file_label = QLabel("")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color:#5d6b7a;")
        form.addRow("组 id:", self.id_edit)
        form.addRow("icon:", self.icon_edit)
        form.addRow("order:", self.order_edit)
        form.addRow("is_name:", self.is_name_combo)
        form.addRow("generic:", self.generic_combo)
        form.addRow("name（标量）:", self.name_edit)
        form.addRow("文件:", self.file_label)
        form_layout.addLayout(form)

        self.entries_summary = QLabel("名称序列：未编辑")
        self.entries_summary.setStyleSheet("color:#5d6b7a;")
        self.entries_btn = QPushButton("✎ 编辑名称序列（结构化块）")
        self.entries_btn.clicked.connect(self._edit_name_entries)
        form_layout.addWidget(self.entries_summary)
        form_layout.addWidget(self.entries_btn)
        form_layout.addStretch(1)

        save_btn = QPushButton("💾 保存（原子写）")
        save_btn.clicked.connect(self._save)
        form_layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)
        root.addWidget(right, 1)

        self._reload()

    def _reload(self):
        if not self.file_path or not os.path.isfile(self.file_path):
            return
        with open(self.file_path, "r", encoding="utf-8-sig",
                  errors="ignore") as f:
            content = f.read()
        self.groups = load_names_groups(content)
        self.sidebar.set_entities([(gid, gid) for gid in sorted(self.groups)])
        self.file_label.setText(self.file_path)

    def _on_select(self, group_id):
        self.current_id = group_id or ""
        g = self.groups.get(group_id)
        if g is None:
            return
        self.id_edit.setText(group_id)
        self.icon_edit.setText(str(g.get("icon", "")))
        self.order_edit.setText(str(g.get("order", "")))
        idx = self.is_name_combo.findText(str(g.get("is_name", "")))
        self.is_name_combo.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.generic_combo.findText(str(g.get("generic", "")))
        self.generic_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.name_edit.setText(str(g.get("name", "")))
        blocks = g.get("blocks") or {}
        name_block = blocks.get("name", "")
        self._name_entries_edited = False
        self._name_entries = _parse_name_entries(name_block)
        if self._name_entries:
            self.entries_summary.setText(
                "名称序列：%d 项" % len(self._name_entries))
        else:
            self.entries_summary.setText(
                "名称序列：无（name 未使用块形式）" if not name_block
                else "名称序列：已保留原始块")

    def _edit_name_entries(self):
        dlg = NameEntriesDialog(self._name_entries or [], parent=self)
        if dlg.exec():
            self._name_entries = dlg.entries
            self._name_entries_edited = True
            self.entries_summary.setText(
                "名称序列：%d 项" % len(self._name_entries))

    def _save(self):
        if not self.current_id:
            QMessageBox.information(self, "保存", "请先选择一个命名组。")
            return
        fields = {
            "icon": self.icon_edit.text().strip(),
            "order": self.order_edit.text().strip(),
            "is_name": self.is_name_combo.currentText().strip(),
            "generic": self.generic_combo.currentText().strip(),
            "name": self.name_edit.text().strip(),
        }
        # 保留已有未知子块；名称块仅在用户编辑后重建
        cur = self.groups.get(self.current_id) or {}
        blocks = dict(cur.get("blocks") or {})
        if self._name_entries_edited:
            if self._name_entries:
                blocks["name"] = _render_name_entries(self._name_entries)
            else:
                blocks.pop("name", None)
        fields["blocks"] = blocks
        try:
            if self.mod_path and not os.path.normcase(self.file_path).startswith(
                    os.path.normcase(self.mod_path)):
                rel = os.path.relpath(self.file_path, self.hoi4_path or os.path.dirname(self.file_path)) \
                    if self.hoi4_path else os.path.basename(self.file_path)
                rel = rel.replace("\\", "/")
                fp, _ = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
            else:
                fp = self.file_path
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
            new_content = save_names_group(content, self.current_id, fields)
            atomic_write_text(fp, new_content)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        QMessageBox.information(self, "已保存", "已保存到:\n%s" % fp)
        self._reload()


def open_names_group_dialog(file_path="", mod_path="", hoi4_path="",
                            parent=None):
    dlg = NamesGroupDialog(file_path=file_path, mod_path=mod_path,
                           hoi4_path=hoi4_path, parent=parent)
    dlg.show()
    return dlg
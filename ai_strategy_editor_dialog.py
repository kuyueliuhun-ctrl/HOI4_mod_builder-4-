"""AI 战略倾向编辑器

- 左侧：策略组列表
- 右侧：`ai_strategy` 表格（type / id / value），支持增删改
- 「✏ 编辑定义」：打开通用树形编辑器（allowed/enable/abort 等完整编辑）
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ai_loader import load_ai_strategies, replace_ai_strategy_entries
from write_utils import atomic_write_text
from state_build_ops import ensure_file_in_mod


class AiStrategyEditorDialog(QDialog):
    """AI 战略倾向专用编辑器。"""

    def __init__(self, groups, mod_path="", hoi4_path="", parent=None,
                 initial_group_id=None):
        super().__init__(parent)
        self.groups = groups
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current = None
        self.setWindowTitle("AI 战略倾向编辑器")
        self.resize(980, 640)
        self._build_ui()
        self._populate_groups(initial_group_id)

    # ---------- UI ----------
    def _build_ui(self):
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("策略组"))
        self.group_list = QListWidget()
        self.group_list.currentItemChanged.connect(self._on_group_changed)
        left.addWidget(self.group_list, 1)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["type", "id", "value"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        right.addWidget(self.table, 1)

        btns = QHBoxLayout()
        add_btn = QPushButton("➕ 添加条目")
        add_btn.clicked.connect(self._add_row)
        btns.addWidget(add_btn)
        del_btn = QPushButton("🗑 删除选中")
        del_btn.clicked.connect(self._del_row)
        btns.addWidget(del_btn)
        tree_btn = QPushButton("✏ 编辑定义（树编辑器）")
        tree_btn.clicked.connect(self._edit_tree)
        btns.addWidget(tree_btn)
        btns.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        right.addLayout(btns)
        root.addLayout(right, 2)

    def _populate_groups(self, initial_group_id=None):
        self.group_list.blockSignals(True)
        self.group_list.clear()
        for gid in sorted(self.groups):
            item = QListWidgetItem(gid)
            item.setData(Qt.ItemDataRole.UserRole, gid)
            self.group_list.addItem(item)
        self.group_list.blockSignals(False)
        if self.group_list.count() > 0:
            target = 0
            if initial_group_id:
                for i in range(self.group_list.count()):
                    if self.group_list.item(i).data(Qt.ItemDataRole.UserRole) == initial_group_id:
                        target = i
                        break
            self.group_list.setCurrentRow(target)
            self._on_group_changed(self.group_list.currentItem())

    def _on_group_changed(self, item):
        if item is None:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        group = self.groups.get(gid)
        if not group:
            return
        self._current = group
        self.id_label.setText("%s  （%s）" % (gid, group.get("file", "")))
        self.table.setRowCount(0)
        for e in group.get("strategies", []):
            self._append_row(e)

    def _append_row(self, entry):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(entry.get("type", "")))
        self.table.setItem(r, 1, QTableWidgetItem(entry.get("id", "")))
        self.table.setItem(r, 2, QTableWidgetItem(entry.get("value", "")))

    def _add_row(self):
        self._append_row({"type": "", "id": "", "value": ""})

    def _del_row(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _entries(self):
        out = []
        for r in range(self.table.rowCount()):
            out.append({
                "type": (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip(),
                "id": (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip(),
                "value": (self.table.item(r, 2).text() if self.table.item(r, 2) else "").strip(),
            })
        return out

    # ---------- 保存 / 树编辑 ----------
    def _edit_tree(self):
        if not self._current:
            return
        fp = self._current.get("file", "")
        mod_fp, copied = self._ensure_writable(fp)
        if not mod_fp:
            QMessageBox.warning(self, "无法编辑", "请先打开 mod 目录")
            return
        self._open_tree_for_file(mod_fp, self._current["id"])

    def _ensure_writable(self, fp):
        if self.mod_path and os.path.normcase(fp).startswith(
                os.path.normcase(os.path.normpath(self.mod_path))):
            return fp, False
        if not self.mod_path or not self.hoi4_path:
            return None, False
        try:
            rel = os.path.relpath(fp, self.hoi4_path).replace("\\", "/")
            if not rel.startswith(".."):
                return ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        except Exception:
            pass
        return None, False

    def _open_tree_for_file(self, fp, entity_id):
        from tree_node import tree_from_pdx_text
        from generic_tree_editor import GenericTreeEditor
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "无法编辑", "读取文件失败：%s" % e)
            return
        root = tree_from_pdx_text(content)
        editor = GenericTreeEditor(
            root_node=root,
            file_path=fp,
            file_lines=content.splitlines(),
            block_range=(1, len(content.splitlines()) + 1),
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            loc_manager=None,
            parent=self,
            title="AI 战略倾向 - %s" % entity_id,
            hoi4_path=self.hoi4_path,
            mod_path=self.mod_path,
        )
        editor.show()
        try:
            model = getattr(editor, "model", None)
            if model is not None:
                results = model.find_nodes(entity_id)
                if results:
                    editor.tree_view.setCurrentIndex(results[0])
                    editor.tree_view.scrollTo(results[0])
        except Exception:
            pass

    def _save(self):
        if not self._current:
            return
        group = self._current
        rel = group.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 战略倾向文件")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "读取文件失败：%s" % e)
            return
        content = replace_ai_strategy_entries(content, group["id"], self._entries())
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        group["strategies"] = self._entries()
        msg = "已保存 AI 战略倾向 %s" % group["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_ai_strategy_editor(file_path, mod_path="", hoi4_path="",
                            entity_id=None, parent=None):
    """按文件/实体打开 AI 战略倾向编辑器。"""
    groups = load_ai_strategies(mod_path, hoi4_path)
    norm = os.path.normpath(file_path).replace("\\", "/")
    file_groups = {}
    for gid, g in groups.items():
        if os.path.normpath(g.get("file", "")).replace("\\", "/") == norm:
            file_groups[gid] = g
    if not file_groups:
        return False
    dlg = AiStrategyEditorDialog(
        file_groups, mod_path, hoi4_path, parent,
        initial_group_id=entity_id if entity_id in file_groups else None)
    dlg.exec()
    return True

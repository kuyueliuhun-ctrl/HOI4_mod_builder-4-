"""AI 海军专用编辑器

三页签：
  - 目标（goals）：可编辑 objective_type / min_priority / max_priority
  - 舰队（fleets）：展示 required/optional taskforces，树编辑器完整编辑
  - 特遣队（taskforces）：展示 mission / 编成，树编辑器完整编辑
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ai_loader import (
    load_ai_navy, replace_top_block_fields,
)
from write_utils import atomic_write_text
from state_build_ops import ensure_file_in_mod


class AiNavyEditorDialog(QDialog):
    """AI 海军专用编辑器。"""

    def __init__(self, navy, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.navy = navy
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("AI 海军编辑器")
        self.resize(1080, 640)
        self._build_ui()
        self._reload_tables()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # 目标页
        self.goals_table = self._make_table(
            ["ID", "objective_type", "min_priority", "max_priority"])
        goals_tab = self._wrap_table(self.goals_table, "目标")
        self.tabs.addTab(goals_tab, "目标")

        # 舰队页
        self.fleets_table = self._make_table(
            ["ID", "required_taskforces", "optional_taskforces"])
        fleets_tab = self._wrap_table(self.fleets_table, "舰队")
        self.tabs.addTab(fleets_tab, "舰队")

        # 特遣队页
        self.taskforces_table = self._make_table(
            ["ID", "mission", "min_composition", "optimal_composition"])
        tf_tab = self._wrap_table(self.taskforces_table, "特遣队")
        self.tabs.addTab(tf_tab, "特遣队")

        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        tree_btn = QPushButton("✏ 编辑选中项（树编辑器）")
        tree_btn.clicked.connect(self._edit_tree_selected)
        footer.addWidget(tree_btn)
        save_btn = QPushButton("💾 保存目标修改")
        save_btn.clicked.connect(self._save_goals)
        footer.addStretch(1)
        footer.addWidget(save_btn)
        root.addLayout(footer)

    def _make_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        return table

    def _wrap_table(self, table, title):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(title))
        lay.addWidget(table)
        return w

    def _reload_tables(self):
        goals = self.navy.get("goals", {})
        self.goals_table.setRowCount(0)
        for gid in sorted(goals):
            g = goals[gid]
            r = self.goals_table.rowCount()
            self.goals_table.insertRow(r)
            self._set(self.goals_table, r, 0, gid)
            self._set(self.goals_table, r, 1, g.get("objective_type", ""))
            self._set(self.goals_table, r, 2, g.get("min_priority", ""))
            self._set(self.goals_table, r, 3, g.get("max_priority", ""))
            self.goals_table.item(r, 0).setData(Qt.ItemDataRole.UserRole, gid)

        fleets = self.navy.get("fleets", {})
        self.fleets_table.setRowCount(0)
        for fid in sorted(fleets):
            f = fleets[fid]
            r = self.fleets_table.rowCount()
            self.fleets_table.insertRow(r)
            self._set(self.fleets_table, r, 0, fid)
            self._set(self.fleets_table, r, 1, self._fmt_map(f.get("required_taskforces", {})))
            self._set(self.fleets_table, r, 2, self._fmt_map(f.get("optional_taskforces", {})))
            self.fleets_table.item(r, 0).setData(Qt.ItemDataRole.UserRole, fid)

        tfs = self.navy.get("taskforces", {})
        self.taskforces_table.setRowCount(0)
        for tid in sorted(tfs):
            t = tfs[tid]
            r = self.taskforces_table.rowCount()
            self.taskforces_table.insertRow(r)
            self._set(self.taskforces_table, r, 0, tid)
            self._set(self.taskforces_table, r, 1, ", ".join(t.get("mission", [])))
            self._set(self.taskforces_table, r, 2, self._fmt_map(t.get("min_composition", {})))
            self._set(self.taskforces_table, r, 3, self._fmt_map(t.get("optimal_composition", {})))
            self.taskforces_table.item(r, 0).setData(Qt.ItemDataRole.UserRole, tid)

    def _set(self, table, row, col, text):
        table.setItem(row, col, QTableWidgetItem(str(text)))

    def _current_table(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            return self.goals_table
        if idx == 1:
            return self.fleets_table
        return self.taskforces_table

    @staticmethod
    def _fmt_map(m):
        if not m:
            return ""
        return ", ".join("%s=%s" % (k, v) for k, v in m.items())

    def _selected_entity(self):
        table = self._current_table()
        rows = sorted({i.row() for i in table.selectedIndexes()})
        if not rows:
            return None
        r = rows[0]
        eid = table.item(r, 0).data(Qt.ItemDataRole.UserRole) if table.item(r, 0) else None
        if self.tabs.currentIndex() == 0:
            ent = self.navy.get("goals", {}).get(eid)
        elif self.tabs.currentIndex() == 1:
            ent = self.navy.get("fleets", {}).get(eid)
        else:
            ent = self.navy.get("taskforces", {}).get(eid)
        return eid, ent

    def _edit_tree_selected(self):
        sel = self._selected_entity()
        if not sel:
            QMessageBox.information(self, "提示", "请先选择一项")
            return
        _eid, ent = sel
        fp = ent.get("file", "")
        if not fp:
            return
        mod_fp, copied = self._ensure_writable(fp)
        if not mod_fp:
            QMessageBox.warning(self, "无法编辑", "请先打开 mod 目录")
            return
        self._open_tree_for_file(mod_fp, ent["id"])

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
            title="AI 海军 - %s" % entity_id,
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

    def _save_goals(self):
        goals = self.navy.get("goals", {})
        saved_any = False
        for r in range(self.goals_table.rowCount()):
            gid_item = self.goals_table.item(r, 0)
            if gid_item is None:
                continue
            gid = gid_item.text().strip()
            g = goals.get(gid)
            if not g:
                continue
            fields = {
                "objective_type": (self.goals_table.item(r, 1).text()
                                   if self.goals_table.item(r, 1) else "").strip(),
                "min_priority": (self.goals_table.item(r, 2).text()
                                 if self.goals_table.item(r, 2) else "").strip(),
                "max_priority": (self.goals_table.item(r, 3).text()
                                 if self.goals_table.item(r, 3) else "").strip(),
            }
            rel = g.get("rel", "")
            if not rel:
                continue
            mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
            if not mod_fp:
                continue
            try:
                with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            content = replace_top_block_fields(content, gid, fields)
            try:
                atomic_write_text(mod_fp, content)
            except Exception:
                continue
            g.update(fields)
            saved_any = True
        if saved_any:
            QMessageBox.information(self, "已保存", "AI 海军目标已保存")
        else:
            QMessageBox.warning(self, "保存失败", "没有可保存的目标")


def open_ai_navy_editor(file_path, mod_path="", hoi4_path="",
                        entity_id=None, parent=None):
    """按文件打开 AI 海军编辑器（同一文件可包含多类，直接打开全量）。"""
    navy = load_ai_navy(mod_path, hoi4_path)
    # 过滤只包含该文件的实体
    norm = os.path.normpath(file_path).replace("\\", "/")
    filtered = {"goals": {}, "fleets": {}, "taskforces": {}}
    for kind in ("goals", "fleets", "taskforces"):
        for eid, ent in navy.get(kind, {}).items():
            if os.path.normpath(ent.get("file", "")).replace("\\", "/") == norm:
                filtered[kind][eid] = ent
    if not any(filtered.values()):
        return False
    dlg = AiNavyEditorDialog(filtered, mod_path, hoi4_path, parent)
    dlg.exec()
    return True

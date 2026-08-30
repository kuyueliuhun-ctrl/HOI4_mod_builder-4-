"""AI 海军专用编辑器（完全专用 UI，不依赖树形编辑器页面）

- 顶部页签：目标 / 舰队 / 特遣队
- 每个页签内左侧固定侧边栏：实体列表 + 搜索 + CRUD
- 主内容：表格概览 + 完整编辑（高级块 ScriptBlockEditorDialog 兜底全部内容）
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QMenu,
    QMessageBox, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QToolButton, QVBoxLayout, QWidget,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_navy_fleet,
    delete_ai_navy_goal,
    delete_ai_navy_taskforce,
    duplicate_ai_navy_fleet,
    duplicate_ai_navy_goal,
    duplicate_ai_navy_taskforce,
    insert_ai_navy_fleet,
    insert_ai_navy_goal,
    insert_ai_navy_taskforce,
    load_ai_navy,
    rename_ai_navy_fleet,
    rename_ai_navy_goal,
    rename_ai_navy_taskforce,
    replace_top_block_fields,
)
from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog, file_tooltip
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

NAVY_OBJECTIVE_TYPES = (
    "convoy_protection", "naval_invasion_support", "amphibious_landing",
    "naval_bombardment", "blockade", "sea_control", "submarine_warfare",
    "naval_superiority", "escort", "mining",
)


class AiNavyEditorDialog(QDialog):
    """AI 海军专用编辑器。"""

    def __init__(self, navy, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.navy = navy
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("AI 海军编辑器")
        self.resize(1240, 740)
        self.setMinimumSize(1120, 660)
        self._build_ui()
        self._reload_tables()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.tabs = QTabWidget()

        # 目标页
        goals_tab, self.goals_sidebar = self._make_kind_tab(
            "goals", "目标", ["ID", "objective_type", "min_priority", "max_priority"],
            self._save_goals)
        self.tabs.addTab(goals_tab, "目标")

        # 舰队页
        fleets_tab, self.fleets_sidebar = self._make_kind_tab(
            "fleets", "舰队", ["ID", "required_taskforces", "optional_taskforces"],
            None)
        self.tabs.addTab(fleets_tab, "舰队")

        # 特遣队页
        tf_tab, self.taskforces_sidebar = self._make_kind_tab(
            "taskforces", "特遣队",
            ["ID", "mission", "min_composition", "optimal_composition"], None)
        self.tabs.addTab(tf_tab, "特遣队")

        root.addWidget(self.tabs, 1)
        self._current_kind = "goals"
        self.goals_table = self._tables["goals"]
        self.fleets_table = self._tables["fleets"]
        self.taskforces_table = self._tables["taskforces"]

    def _make_kind_tab(self, kind, title, headers, save_handler):
        """构造一个页签：左固定侧边栏 + 右表 + 完整编辑/保存。"""
        page = QWidget()
        h = QHBoxLayout(page)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        sidebar = EntityListSidebar(title, self)
        sidebar.set_paths(self.mod_path, self.hoi4_path)
        sidebar.currentChanged.connect(
            lambda eid, k=kind: self._on_kind_entity_changed(k, eid))
        sidebar.createRequested.connect(
            lambda: self._create_entity(kind))
        sidebar.duplicateRequested.connect(
            lambda: self._duplicate_entity(kind))
        sidebar.renameRequested.connect(
            lambda: self._rename_entity(kind))
        sidebar.deleteRequested.connect(
            lambda: self._delete_entity(kind))
        h.addWidget(sidebar)

        right = QVBoxLayout()
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.addWidget(table, 1)

        btns = QHBoxLayout()
        adv_btn = QToolButton()
        adv_btn.setText("高级 ▾")
        adv_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        raw_menu = QMenu(adv_btn)
        raw_act = raw_menu.addAction("高级：原始 PDX（兜底）")
        raw_act.triggered.connect(
            lambda checked=False, k=kind: self._edit_raw_selected(k))
        adv_btn.setMenu(raw_menu)
        btns.addWidget(adv_btn)
        if save_handler is not None:
            save_btn = QPushButton("💾 保存目标修改")
            save_btn.clicked.connect(save_handler)
            btns.addWidget(save_btn)
        btns.addStretch(1)
        right.addLayout(btns)
        h.addLayout(right, 1)

        self._tables = getattr(self, "_tables", {})
        self._tables[kind] = table
        return page, sidebar

    # ---------- 数据填充 ----------
    def _entities_of(self, kind):
        return self.navy.get(kind, {})

    def _reload_tables(self):
        for kind in ("goals", "fleets", "taskforces"):
            ents = self._entities_of(kind)
            items = [(eid, eid, file_tooltip(ents.get(eid), getattr(self, "mod_path", ""), getattr(self, "hoi4_path", ""))
                      or eid) for eid in sorted(ents)]
            getattr(self, "%s_sidebar" % kind).set_entities(items)
            table = self._tables[kind]
            table.setRowCount(0)
            if kind == "goals":
                self._fill_goals_table()
            elif kind == "fleets":
                self._fill_fleets_table()
            else:
                self._fill_taskforces_table()

    def _fill_goals_table(self):
        table = self._tables["goals"]
        table.setRowCount(0)
        for gid in sorted(self.navy.get("goals", {})):
            g = self.navy["goals"][gid]
            r = table.rowCount()
            table.insertRow(r)
            self._set(table, r, 0, gid)
            self._set(table, r, 1, g.get("objective_type", ""))
            combo = QComboBox()
            combo.addItems(NAVY_OBJECTIVE_TYPES)
            combo.setEditable(True)
            combo.setCurrentText(g.get("objective_type", ""))
            table.setCellWidget(r, 1, combo)
            self._set(table, r, 2, g.get("min_priority", ""))
            self._set(table, r, 3, g.get("max_priority", ""))
            table.item(r, 0).setData(Qt.ItemDataRole.UserRole, gid)

    def _fill_fleets_table(self):
        table = self._tables["fleets"]
        table.setRowCount(0)
        for fid in sorted(self.navy.get("fleets", {})):
            f = self.navy["fleets"][fid]
            r = table.rowCount()
            table.insertRow(r)
            self._set(table, r, 0, fid)
            self._set(table, r, 1, self._fmt_map(f.get("required_taskforces", {})))
            self._set(table, r, 2, self._fmt_map(f.get("optional_taskforces", {})))
            table.item(r, 0).setData(Qt.ItemDataRole.UserRole, fid)

    def _fill_taskforces_table(self):
        table = self._tables["taskforces"]
        table.setRowCount(0)
        for tid in sorted(self.navy.get("taskforces", {})):
            t = self.navy["taskforces"][tid]
            r = table.rowCount()
            table.insertRow(r)
            self._set(table, r, 0, tid)
            self._set(table, r, 1, ", ".join(t.get("mission", [])))
            self._set(table, r, 2, self._fmt_map(t.get("min_composition", {})))
            self._set(table, r, 3, self._fmt_map(t.get("optimal_composition", {})))
            table.item(r, 0).setData(Qt.ItemDataRole.UserRole, tid)

    def _set(self, table, row, col, text):
        table.setItem(row, col, QTableWidgetItem(str(text)))

    @staticmethod
    def _fmt_map(m):
        if not m:
            return ""
        return ", ".join("%s=%s" % (k, v) for k, v in m.items())

    # ---------- 选择 ----------
    def _on_kind_entity_changed(self, kind, eid):
        self._current_kind = kind

    def _selected_entity(self, kind):
        sidebar = getattr(self, "%s_sidebar" % kind)
        eid = sidebar.current_id()
        if not eid:
            return None, None
        return eid, self._entities_of(kind).get(eid)

    # ---------- 完整编辑 ----------
    def _edit_raw_selected(self, kind):
        eid, ent = self._selected_entity(kind)
        if not ent:
            QMessageBox.information(self, "提示", "请先选择一项")
            return
        fp = ent.get("file", "")
        mod_fp, copied = self._ensure_writable(fp)
        if not mod_fp:
            return
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=ent.get("raw", ""),
            block_key=eid,
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="AI 海军 %s - %s" % (kind, eid),
        )
        if dlg.exec():
            ent["raw"] = dlg.get_block_text()
            # 保存整块到文件
            rel = ent.get("rel", "")
            if rel:
                mod_fp2, _c2 = ensure_file_in_mod(
                    self.mod_path, self.hoi4_path, rel)
                if mod_fp2:
                    try:
                        with open(mod_fp2, "r", encoding="utf-8-sig",
                                  errors="ignore") as f:
                            content = f.read()
                        content = self._replace_block(content, eid, dlg.get_block_text())
                        atomic_write_text(mod_fp2, content)
                    except Exception as e:
                        QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)

    def _replace_block(self, content, eid, new_text):
        # 顶层块整体替换
        from ai_loader import _top_block
        bounds = _top_block(content, eid)
        if bounds is None:
            return content
        start, end = bounds
        return content[:start] + new_text.strip() + content[end:]

    # ---------- CRUD ----------
    def _create_entity(self, kind):
        new_id, ok = QInputDialog.getText(self, "新建 %s" % kind, "ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self._entities_of(kind):
            QMessageBox.warning(self, "错误", "已存在：%s" % new_id)
            return
        self._apply_crud(kind, "create", new_id.strip())

    def _duplicate_entity(self, kind):
        eid, ent = self._selected_entity(kind)
        if not ent:
            return
        new_id, ok = QInputDialog.getText(
            self, "复制 %s" % kind, "新 ID：", text=eid + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self._entities_of(kind):
            QMessageBox.warning(self, "错误", "已存在：%s" % new_id)
            return
        self._apply_crud(kind, "duplicate", eid, new_id.strip())

    def _rename_entity(self, kind):
        eid, ent = self._selected_entity(kind)
        if not ent:
            return
        new_id, ok = QInputDialog.getText(
            self, "重命名 %s" % kind, "新 ID：", text=eid)
        if not ok or not new_id.strip() or new_id.strip() == eid:
            return
        if new_id.strip() in self._entities_of(kind):
            QMessageBox.warning(self, "错误", "已存在：%s" % new_id)
            return
        self._apply_crud(kind, "rename", eid, new_id.strip())

    def _delete_entity(self, kind):
        eid, ent = self._selected_entity(kind)
        if not ent:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除 %s '%s' 吗？" % (kind, eid))
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._apply_crud(kind, "delete", eid)

    def _apply_crud(self, kind, op, eid, new_id=None):
        ent = None
        if op == "create":
            ent = {"id": eid, "rel": self._any_rel_for(kind)}
        else:
            _, ent = self._selected_entity(kind)
        if not ent:
            return
        rel = ent.get("rel", "")
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        if kind == "goals":
            if op == "create":
                content = insert_ai_navy_goal(content, eid)
            elif op == "delete":
                content = delete_ai_navy_goal(content, eid)
            elif op == "rename":
                content = rename_ai_navy_goal(content, eid, new_id)
            elif op == "duplicate":
                content = duplicate_ai_navy_goal(content, eid, new_id)
        elif kind == "fleets":
            if op == "create":
                content = insert_ai_navy_fleet(content, eid)
            elif op == "delete":
                content = delete_ai_navy_fleet(content, eid)
            elif op == "rename":
                content = rename_ai_navy_fleet(content, eid, new_id)
            elif op == "duplicate":
                content = duplicate_ai_navy_fleet(content, eid, new_id)
        else:
            if op == "create":
                content = insert_ai_navy_taskforce(content, eid)
            elif op == "delete":
                content = delete_ai_navy_taskforce(content, eid)
            elif op == "rename":
                content = rename_ai_navy_taskforce(content, eid, new_id)
            elif op == "duplicate":
                content = duplicate_ai_navy_taskforce(content, eid, new_id)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        self._reload_all()

    def _any_rel_for(self, kind):
        # 找一个同类实体以复用文件路径
        for eid, ent in self._entities_of(kind).items():
            return ent.get("rel", "")
        return ""

    # ---------- 保存目标 ----------
    def _save_goals(self):
        goals = self.navy.get("goals", {})
        saved_any = False
        table = self._tables["goals"]
        for r in range(table.rowCount()):
            gid_item = table.item(r, 0)
            if gid_item is None:
                continue
            gid = gid_item.text().strip()
            g = goals.get(gid)
            if not g:
                continue
            combo = table.cellWidget(r, 1)
            obj_type = combo.currentText().strip() if isinstance(combo, QComboBox) else (
                table.item(r, 1).text() if table.item(r, 1) else "")
            fields = {
                "objective_type": obj_type,
                "min_priority": (table.item(r, 2).text() if table.item(r, 2) else "").strip(),
                "max_priority": (table.item(r, 3).text() if table.item(r, 3) else "").strip(),
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

    # ---------- 辅助 ----------
    def _ensure_writable(self, fp):
        if not fp:
            return None, False
        fp = os.path.normpath(fp)
        if self.mod_path and os.path.normcase(fp).startswith(
                os.path.normcase(os.path.normpath(self.mod_path))):
            return fp, False
        if not self.mod_path:
            return None, False
        if self.hoi4_path:
            try:
                rel = os.path.relpath(fp, self.hoi4_path)
                if not rel.startswith(".."):
                    return ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
            except Exception:
                pass
        return None, False

    def _reload_all(self):
        _AI_CACHE.pop(("ai_navy", self.mod_path or "",
                       self.hoi4_path or ""), None)
        self.navy = load_ai_navy(self.mod_path, self.hoi4_path)
        self._reload_tables()


def open_ai_navy_editor(file_path, mod_path="", hoi4_path="",
                        entity_id=None, parent=None):
    """按文件打开 AI 海军编辑器（同一文件可包含多类，直接打开全量）。"""
    navy = load_ai_navy(mod_path, hoi4_path)
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

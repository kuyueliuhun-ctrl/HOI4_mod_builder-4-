"""AI 战略倾向编辑器（完全专用 UI，不依赖树形编辑器页面）

- 左侧固定侧边栏：策略组列表 + 搜索 + 新建/复制/重命名/删除
- 主内容：`ai_strategy` 表格（type / id / value）+ 高级脚本块
  （allowed / enable / abort 通过 ScriptBlockEditorDialog 编辑）
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_strategy_group,
    duplicate_ai_strategy_group,
    insert_ai_strategy_group,
    load_ai_strategies,
    rename_ai_strategy_group,
    replace_ai_strategy_entries,
    upsert_top_block_child,
)
from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog, file_tooltip
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

ADVANCED_FIELDS = ("allowed", "enable", "abort")

# AI 战略倾向 type 枚举（operative_* 时可用特工字段）
STRATEGY_TYPE_CHOICES = (
    "army_ratio", "navy_ratio", "air_ratio", "role_ratio",
    "production_ratio", "technology_slot", "research_slot",
    "operative_leader", "operative_network", "operative_mission",
    "faction_priority", "diplomatic_action", "country_priority",
    "convoys", "lend_lease", "volunteer_ratio", "reinforce_priority",
    "air_mission", "naval_mission", "division_template",
    "equipment_design", "mio_priority", "building_priority",
    "state_priority", "custom",
)


class AiStrategyEditorDialog(QDialog):
    """AI 战略倾向专用编辑器。"""

    def __init__(self, groups, mod_path="", hoi4_path="", parent=None,
                 initial_group_id=None):
        super().__init__(parent)
        self.groups = groups
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current = None
        self._advanced_blocks = {}  # field -> block_text
        self.setWindowTitle("AI 战略倾向编辑器")
        self.resize(1100, 720)
        self.setMinimumSize(1000, 640)
        self._build_ui()
        self._populate_groups(initial_group_id)

    # ---------- UI ----------
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("策略组", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_group_changed)
        self.sidebar.createRequested.connect(self._create_group)
        self.sidebar.duplicateRequested.connect(self._duplicate_group)
        self.sidebar.renameRequested.connect(self._rename_group)
        self.sidebar.deleteRequested.connect(self._delete_group)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["type", "id", "value"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.addWidget(self.table, 1)

        row_btns = QHBoxLayout()
        add_btn = QPushButton("➕ 添加条目")
        del_btn = QPushButton("🗑 删除选中")
        up_btn = QPushButton("⬆ 上移")
        down_btn = QPushButton("⬇ 下移")
        add_btn.clicked.connect(self._add_row)
        del_btn.clicked.connect(self._del_row)
        up_btn.clicked.connect(self._move_row_up)
        down_btn.clicked.connect(self._move_row_down)
        for b in (add_btn, del_btn, up_btn, down_btn):
            row_btns.addWidget(b)
        row_btns.addStretch(1)
        right.addLayout(row_btns)

        # 高级脚本块
        adv_label = QLabel("高级脚本块（allowed / enable / abort）")
        adv_label.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        right.addWidget(adv_label)
        self.adv_buttons = {}
        for field in ADVANCED_FIELDS:
            row = QHBoxLayout()
            name = QLabel(field)
            name.setMinimumWidth(80)
            row.addWidget(name)
            summary = QPushButton("未编辑")
            summary.setToolTip("点击打开高级块编辑器")
            summary.clicked.connect(
                lambda checked=False, f=field: self._edit_advanced(f))
            row.addWidget(summary, 1)
            self.adv_buttons[field] = summary
            right.addLayout(row)

        footer = QHBoxLayout()
        footer.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)
        right.addLayout(footer)
        root.addLayout(right, 1)

    def _populate_groups(self, initial_group_id=None):
        items = [(gid, gid, file_tooltip(self.groups.get(gid), getattr(self, "mod_path", ""), getattr(self, "hoi4_path", ""))
                  or gid) for gid in sorted(self.groups)]
        self.sidebar.set_entities(items)
        if initial_group_id:
            self.sidebar.set_current(initial_group_id)
        elif self.sidebar.current_id() is None and self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    # ---------- 列表切换 ----------
    def _on_group_changed(self, group_id):
        if group_id is None:
            self._current = None
            self.id_label.setText("—")
            self.table.setRowCount(0)
            return
        group = self.groups.get(group_id)
        if not group:
            return
        self._current = group
        self._advanced_blocks = {
            f: group.get(f, "") or "" for f in ADVANCED_FIELDS}
        self.id_label.setText("%s  （%s）" % (group_id, group.get("file", "")))
        self.table.setRowCount(0)
        for e in group.get("strategies", []):
            self._append_row(e)
        self._update_advanced_summaries()

    def _append_row(self, entry):
        r = self.table.rowCount()
        self.table.insertRow(r)
        type_text = entry.get("type", "") or ""
        type_item = QTableWidgetItem(type_text)
        self.table.setItem(r, 0, type_item)
        combo = QComboBox()
        combo.addItems(STRATEGY_TYPE_CHOICES)
        combo.setCurrentText(type_text if type_text in STRATEGY_TYPE_CHOICES else "custom")
        combo.setEditable(True)
        self.table.setCellWidget(r, 0, combo)
        self.table.setItem(r, 1, QTableWidgetItem(entry.get("id", "")))
        self.table.setItem(r, 2, QTableWidgetItem(entry.get("value", "")))

    def _entries(self):
        out = []
        for r in range(self.table.rowCount()):
            type_widget = self.table.cellWidget(r, 0)
            if isinstance(type_widget, QComboBox):
                type_text = type_widget.currentText().strip()
            else:
                item = self.table.item(r, 0)
                type_text = (item.text() if item else "").strip()
            out.append({
                "type": type_text,
                "id": (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip(),
                "value": (self.table.item(r, 2).text() if self.table.item(r, 2) else "").strip(),
            })
        return out

    # ---------- 行操作 ----------
    def _add_row(self):
        self._append_row({"type": "", "id": "", "value": ""})

    def _del_row(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _move_row_up(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows or rows[0] <= 0:
            return
        r = rows[0]
        self.table.insertRow(r - 1)
        for c in range(3):
            item = self.table.takeItem(r + 1, c)
            self.table.setItem(r - 1, c, item)
        self.table.removeRow(r + 1)
        self.table.selectRow(r - 1)

    def _move_row_down(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows or rows[-1] >= self.table.rowCount() - 1:
            return
        r = rows[-1]
        self.table.insertRow(r + 2)
        for c in range(3):
            item = self.table.takeItem(r, c)
            self.table.setItem(r + 2, c, item)
        self.table.removeRow(r)
        self.table.selectRow(r + 1)

    # ---------- 高级块 ----------
    def _update_advanced_summaries(self):
        for field in ADVANCED_FIELDS:
            text = (self._advanced_blocks.get(field) or "").strip()
            if not text:
                self.adv_buttons[field].setText("空")
            else:
                lines = text.splitlines()
                self.adv_buttons[field].setText("已编辑（%d 行）" % len(lines))

    def _edit_advanced(self, field):
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=self._advanced_blocks.get(field, ""),
            block_key=field,
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="编辑 %s" % field,
        )
        if dlg.exec():
            self._advanced_blocks[field] = dlg.get_block_text()
            self._update_advanced_summaries()

    # ---------- CRUD ----------
    def _write_current_file(self, content):
        group = self._current
        if group is None:
            return None, False
        rel = group.get("rel", "")
        if not rel:
            return None, False
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return None, False
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return None, False
        return mod_fp, copied

    def _reload_groups(self, keep_id=None):
        _AI_CACHE.pop(("ai_strategy", self.mod_path or "",
                       self.hoi4_path or ""), None)
        self.groups = load_ai_strategies(self.mod_path, self.hoi4_path)
        self._populate_groups(keep_id)

    def _create_group(self):
        if not self._current:
            return
        group = self._current
        rel = group.get("rel", "")
        if not rel:
            return
        new_id, ok = QInputDialog.getText(self, "新建策略组", "策略组 ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.groups:
            QMessageBox.warning(self, "错误", "策略组已存在：%s" % new_id)
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "错误", "请先打开 mod 目录")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "错误", "读取文件失败：%s" % e)
            return
        content = insert_ai_strategy_group(content, new_id.strip())
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        self._reload_groups(new_id.strip())

    def _duplicate_group(self):
        if not self._current:
            return
        group = self._current
        old_id = group["id"]
        new_id, ok = QInputDialog.getText(
            self, "复制策略组", "新策略组 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.groups:
            QMessageBox.warning(self, "错误", "策略组已存在：%s" % new_id)
            return
        rel = group.get("rel", "")
        if not rel:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_strategy_group(
            content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(new_id.strip())

    def _rename_group(self):
        if not self._current:
            return
        group = self._current
        old_id = group["id"]
        new_id, ok = QInputDialog.getText(
            self, "重命名策略组", "新策略组 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if new_id.strip() in self.groups:
            QMessageBox.warning(self, "错误", "策略组已存在：%s" % new_id)
            return
        rel = group.get("rel", "")
        if not rel:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_strategy_group(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload_groups(new_id.strip())

    def _delete_group(self):
        if not self._current:
            return
        group = self._current
        reply = QMessageBox.question(
            self, "确认", "确定要删除策略组 '%s' 吗？" % group["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        rel = group.get("rel", "")
        if not rel:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_strategy_group(content, group["id"])
        atomic_write_text(mod_fp, content)
        self._reload_groups()

    # ---------- 保存 ----------
    def _save(self):
        if not self._current:
            return
        group = self._current
        rel = group.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 战略倾向文件")
            return
        try:
            with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "读取文件失败：%s" % e)
            return
        content = replace_ai_strategy_entries(
            content, group["id"], self._entries())
        for field in ADVANCED_FIELDS:
            text = (self._advanced_blocks.get(field) or "").strip()
            if text:
                content = upsert_top_block_child(
                    content, group["id"], field, text)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        group["strategies"] = self._entries()
        for field in ADVANCED_FIELDS:
            group[field] = self._advanced_blocks.get(field, "")
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

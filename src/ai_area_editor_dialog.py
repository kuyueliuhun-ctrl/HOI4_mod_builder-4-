"""AI 区域专用编辑器（完全专用 UI，不依赖树形编辑器页面）

- 左侧固定侧边栏：区域列表 + 搜索 + CRUD
- 主内容：strategic_regions 列表编辑器 + 原始块编辑（ScriptBlockEditorDialog 兜底）
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPushButton, QToolButton,
    QVBoxLayout,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_area,
    duplicate_ai_area,
    insert_ai_area,
    load_ai_areas,
    rename_ai_area,
    replace_ai_area_block,
    replace_ai_area_regions,
)
from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog, file_tooltip
from ui_widgets import source_badge
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text


class AiAreaEditorDialog(QDialog):
    """AI 区域专用编辑器。"""

    def __init__(self, areas, mod_path="", hoi4_path="", parent=None,
                 initial_area_id=None):
        super().__init__(parent)
        self.areas = areas
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current = None
        self.setWindowTitle("AI 区域编辑器")
        self.resize(1000, 680)
        self.setMinimumSize(920, 600)
        self._build_ui()
        self._populate(initial_area_id)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("AI 区域", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_area_changed)
        self.sidebar.createRequested.connect(self._create_area)
        self.sidebar.duplicateRequested.connect(self._duplicate_area)
        self.sidebar.renameRequested.connect(self._rename_area)
        self.sidebar.deleteRequested.connect(self._delete_area)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)
        self.source_label = source_badge()
        right.addWidget(self.source_label)

        right.addWidget(QLabel("strategic_regions"))
        self.regions_list = QListWidget()
        self.regions_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.addWidget(self.regions_list, 1)

        btns = QHBoxLayout()
        add_btn = QPushButton("＋ 添加")
        edit_btn = QPushButton("✏ 编辑选中")
        del_btn = QPushButton("🗑 删除选中")
        up_btn = QPushButton("⬆")
        down_btn = QPushButton("⬇")
        add_btn.clicked.connect(self._add_region)
        edit_btn.clicked.connect(self._edit_region)
        del_btn.clicked.connect(self._del_region)
        up_btn.clicked.connect(self._move_up)
        down_btn.clicked.connect(self._move_down)
        for b in (add_btn, edit_btn, del_btn, up_btn, down_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        right.addLayout(btns)

        raw_row = QHBoxLayout()
        advanced_btn = QToolButton()
        advanced_btn.setText("高级 ▾")
        advanced_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        raw_menu = QMenu(advanced_btn)
        raw_act = raw_menu.addAction("高级：原始 PDX（兜底）")
        raw_act.setToolTip("用高级块编辑器查看/编辑该区域的全部内容（含未知字段）")
        raw_act.triggered.connect(self._edit_raw)
        advanced_btn.setMenu(raw_menu)
        raw_row.addWidget(advanced_btn)
        raw_row.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        raw_row.addWidget(save_btn)
        right.addLayout(raw_row)
        root.addLayout(right, 1)

    def _populate(self, initial_area_id=None):
        items = [(aid, aid, file_tooltip(self.areas.get(aid), getattr(self, "mod_path", ""), getattr(self, "hoi4_path", ""))
                  or aid) for aid in sorted(self.areas)]
        self.sidebar.set_entities(items)
        if initial_area_id:
            self.sidebar.set_current(initial_area_id)
        elif self.sidebar.current_id() is None and self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    def _on_area_changed(self, area_id):
        if area_id is None:
            self._current = None
            self.id_label.setText("—")
            self.regions_list.clear()
            return
        area = self.areas.get(area_id)
        if not area:
            return
        self._current = area
        self.id_label.setText("%s  （%s）" % (area_id, area.get("file", "")))
        fp = area.get("file", "") or ""
        src = "game"
        if self.mod_path and fp and os.path.normpath(fp).startswith(
                os.path.normpath(self.mod_path)):
            src = "mod"
        self.source_label.setText(source_badge(src).text())
        self.regions_list.blockSignals(True)
        self.regions_list.clear()
        for r in area.get("strategic_regions", []):
            item = QListWidgetItem(str(r))
            item.setToolTip(str(r))
            self.regions_list.addItem(item)
        self.regions_list.blockSignals(False)

    # ---------- 区域列表操作 ----------
    def _regions(self):
        out = []
        for i in range(self.regions_list.count()):
            text = self.regions_list.item(i).text().strip()
            if text:
                out.append(text)
        return out

    def _add_region(self):
        text, ok = QInputDialog.getText(self, "添加战略区域", "区域 ID：")
        if ok and text.strip():
            self.regions_list.addItem(text.strip())

    def _edit_region(self):
        item = self.regions_list.currentItem()
        if item is None:
            QMessageBox.information(self, "提示", "请先选择一项")
            return
        text, ok = QInputDialog.getText(
            self, "编辑战略区域", "区域 ID：", text=item.text())
        if ok and text.strip():
            item.setText(text.strip())
            item.setToolTip(text.strip())

    def _del_region(self):
        rows = sorted({i.row() for i in self.regions_list.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.regions_list.takeItem(r)

    def _move_up(self):
        row = self.regions_list.currentRow()
        if row > 0:
            item = self.regions_list.takeItem(row)
            self.regions_list.insertItem(row - 1, item)
            self.regions_list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.regions_list.currentRow()
        if 0 <= row < self.regions_list.count() - 1:
            item = self.regions_list.takeItem(row)
            self.regions_list.insertItem(row + 1, item)
            self.regions_list.setCurrentRow(row + 1)

    # ---------- 原始块 ----------
    def _edit_raw(self):
        if not self._current:
            return
        from gui_translator import get_translator
        from focus_view import CUSTOM_STATEMENT_PATH
        dlg = ScriptBlockEditorDialog(
            block_text=self._current.get("raw", ""),
            block_key=self._current["id"],
            translator=get_translator(),
            custom_statement_path=CUSTOM_STATEMENT_PATH,
            parent=self,
            title="AI 区域 - %s" % self._current["id"],
        )
        if dlg.exec():
            self._current["raw"] = dlg.get_block_text()
            # 同步已解析字段，避免保存后列表与原始块不一致
            self._current["strategic_regions"] = self._regions()

    # ---------- CRUD ----------
    def _write_file(self, content):
        if not self._current:
            return None, False
        rel = self._current.get("rel", "")
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

    def _reload(self, keep_id=None):
        _AI_CACHE.pop(("ai_areas", self.mod_path or "",
                       self.hoi4_path or ""), None)
        self.areas = load_ai_areas(self.mod_path, self.hoi4_path)
        # 过滤到当前文件（保持与打开时一致）
        if self._current:
            norm = os.path.normpath(self._current.get("file", "")).replace("\\", "/")
            self.areas = {aid: a for aid, a in self.areas.items()
                          if os.path.normpath(a.get("file", "")).replace("\\", "/") == norm}
        self._populate(keep_id)

    def _create_area(self):
        if not self._current:
            return
        area = self._current
        new_id, ok = QInputDialog.getText(self, "新建区域", "区域 ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.areas:
            QMessageBox.warning(self, "错误", "区域已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, area.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_area(content, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _duplicate_area(self):
        if not self._current:
            return
        old_id = self._current["id"]
        new_id, ok = QInputDialog.getText(
            self, "复制区域", "新区域 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.areas:
            QMessageBox.warning(self, "错误", "区域已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_area(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _rename_area(self):
        if not self._current:
            return
        old_id = self._current["id"]
        new_id, ok = QInputDialog.getText(
            self, "重命名区域", "新区域 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if new_id.strip() in self.areas:
            QMessageBox.warning(self, "错误", "区域已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_area(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _delete_area(self):
        if not self._current:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除区域 '%s' 吗？" % self._current["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_area(content, self._current["id"])
        atomic_write_text(mod_fp, content)
        self._reload()

    # ---------- 保存 ----------
    def _save(self):
        if not self._current:
            return
        area = self._current
        rel = area.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 区域文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = replace_ai_area_regions(content, area["id"], self._regions())
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        area["strategic_regions"] = self._regions()
        msg = "已保存 AI 区域 %s" % area["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_ai_area_editor(file_path, mod_path="", hoi4_path="",
                        entity_id=None, parent=None):
    """按文件/实体打开 AI 区域编辑器。"""
    areas = load_ai_areas(mod_path, hoi4_path)
    norm = os.path.normpath(file_path).replace("\\", "/")
    file_areas = {}
    for aid, a in areas.items():
        if os.path.normpath(a.get("file", "")).replace("\\", "/") == norm:
            file_areas[aid] = a
    if not file_areas:
        return False
    dlg = AiAreaEditorDialog(
        file_areas, mod_path, hoi4_path, parent,
        initial_area_id=entity_id if entity_id in file_areas else None)
    dlg.exec()
    return True

"""AI 派系战区专用编辑器（完全专用 UI，不依赖树形编辑器页面）

- 左侧固定侧边栏：战区列表 + 搜索 + CRUD
- 主内容：name / can_skip_first_region / regions / preferred_countries +
  高级块（cancel / ai_will_do 通过 ScriptBlockEditorDialog）
- 保存：原版自动复制到 mod + 原子写
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPushButton, QToolButton,
    QVBoxLayout,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_faction_theater,
    duplicate_ai_faction_theater,
    insert_ai_faction_theater,
    load_ai_faction_theaters,
    rename_ai_faction_theater,
    replace_ai_region_list,
    replace_top_block_field,
    upsert_top_block_child,
)
from ai_ui_common import EntityListSidebar, ScriptBlockEditorDialog, file_tooltip
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

LIST_FIELDS = ("regions", "preferred_countries")
ADVANCED_FIELDS = ("cancel", "ai_will_do")


class AiFactionTheaterEditorDialog(QDialog):
    """AI 派系战区专用编辑器。"""

    def __init__(self, theaters, mod_path="", hoi4_path="", parent=None,
                 initial_id=None):
        super().__init__(parent)
        self.theaters = theaters
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current = None
        self._advanced_blocks = {}
        self.setWindowTitle("AI 派系战区编辑器")
        self.resize(1100, 720)
        self.setMinimumSize(1000, 640)
        self._build_ui()
        self._populate(initial_id)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("派系战区", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_theater_changed)
        self.sidebar.createRequested.connect(self._create_theater)
        self.sidebar.duplicateRequested.connect(self._duplicate_theater)
        self.sidebar.renameRequested.connect(self._rename_theater)
        self.sidebar.deleteRequested.connect(self._delete_theater)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)

        form = QHBoxLayout()
        form.addWidget(QLabel("name"))
        self.name_edit = QLineEdit()
        form.addWidget(self.name_edit, 1)
        form.addWidget(QLabel("can_skip_first_region"))
        self.skip_edit = QLineEdit()
        self.skip_edit.setMaximumWidth(120)
        form.addWidget(self.skip_edit)
        right.addLayout(form)

        # 列表字段
        self.list_widgets = {}
        for field in LIST_FIELDS:
            right.addWidget(QLabel(field))
            lst = QListWidget()
            lst.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            right.addWidget(lst, 1)
            self.list_widgets[field] = lst

        list_btns = QHBoxLayout()
        for field in LIST_FIELDS:
            add_btn = QPushButton("＋ %s 添加" % field)
            del_btn = QPushButton("🗑 %s 删除" % field)
            add_btn.clicked.connect(
                lambda checked=False, f=field: self._add_list_item(f))
            del_btn.clicked.connect(
                lambda checked=False, f=field: self._del_list_item(f))
            list_btns.addWidget(add_btn)
            list_btns.addWidget(del_btn)
        list_btns.addStretch(1)
        right.addLayout(list_btns)

        # 高级块
        adv_label = QLabel("高级脚本块（cancel / ai_will_do）")
        adv_label.setStyleSheet("font-weight:bold; color:#1f4f7e;")
        right.addWidget(adv_label)
        self.adv_buttons = {}
        for field in ADVANCED_FIELDS:
            row = QHBoxLayout()
            row.addWidget(QLabel(field))
            btn = QPushButton("未编辑")
            btn.clicked.connect(
                lambda checked=False, f=field: self._edit_advanced(f))
            row.addWidget(btn, 1)
            self.adv_buttons[field] = btn
            right.addLayout(row)

        footer = QHBoxLayout()
        advanced_btn = QToolButton()
        advanced_btn.setText("高级 ▾")
        advanced_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        raw_menu = QMenu(advanced_btn)
        raw_act = raw_menu.addAction("高级：原始 PDX（兜底）")
        raw_act.triggered.connect(self._edit_raw)
        advanced_btn.setMenu(raw_menu)
        footer.addWidget(advanced_btn)
        footer.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)
        right.addLayout(footer)
        root.addLayout(right, 1)

    def _populate(self, initial_id=None):
        items = [(tid,
                  ("%s (%s)" % (tid, t.get("name", ""))) if t.get("name")
                  else tid,
                  file_tooltip(t, getattr(self, "mod_path", ""), getattr(self, "hoi4_path", "")) or tid)
                 for tid, t in sorted(self.theaters.items())]
        self.sidebar.set_entities(items)
        if initial_id:
            self.sidebar.set_current(initial_id)
        elif self.sidebar.current_id() is None and self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    def _on_theater_changed(self, theater_id):
        if theater_id is None:
            self._current = None
            self.id_label.setText("—")
            return
        t = self.theaters.get(theater_id)
        if not t:
            return
        self._current = t
        self._advanced_blocks = {
            f: t.get(f, "") or "" for f in ADVANCED_FIELDS}
        self.id_label.setText("%s  （%s）" % (theater_id, t.get("file", "")))
        self.name_edit.setText(t.get("name", ""))
        self.skip_edit.setText(t.get("can_skip_first_region", ""))
        for field in LIST_FIELDS:
            lst = self.list_widgets[field]
            lst.blockSignals(True)
            lst.clear()
            for v in t.get(field, []) or []:
                item = QListWidgetItem(str(v))
                item.setToolTip(str(v))
                lst.addItem(item)
            lst.blockSignals(False)
        self._update_advanced_summaries()

    def _list_values(self, field):
        lst = self.list_widgets[field]
        return [lst.item(i).text().strip()
                for i in range(lst.count()) if lst.item(i).text().strip()]

    def _add_list_item(self, field):
        text, ok = QInputDialog.getText(self, "添加 %s" % field, "值：")
        if ok and text.strip():
            self.list_widgets[field].addItem(text.strip())

    def _del_list_item(self, field):
        lst = self.list_widgets[field]
        rows = sorted({i.row() for i in lst.selectedIndexes()}, reverse=True)
        for r in rows:
            lst.takeItem(r)

    def _update_advanced_summaries(self):
        for field in ADVANCED_FIELDS:
            text = (self._advanced_blocks.get(field) or "").strip()
            self.adv_buttons[field].setText(
                "空" if not text else "已编辑（%d 行）" % len(text.splitlines()))

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
            title="AI 派系战区 - %s" % self._current["id"],
        )
        if dlg.exec():
            self._current["raw"] = dlg.get_block_text()

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
        _AI_CACHE.pop(("ai_faction_theaters", self.mod_path or "",
                       self.hoi4_path or ""), None)
        all_t = load_ai_faction_theaters(self.mod_path, self.hoi4_path)
        if self._current:
            norm = os.path.normpath(self._current.get("file", "")).replace("\\", "/")
            all_t = {tid: t for tid, t in all_t.items()
                     if os.path.normpath(t.get("file", "")).replace("\\", "/") == norm}
        self.theaters = all_t
        self._populate(keep_id)

    def _create_theater(self):
        if not self._current:
            return
        new_id, ok = QInputDialog.getText(self, "新建战区", "战区 ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.theaters:
            QMessageBox.warning(self, "错误", "战区已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_faction_theater(content, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _duplicate_theater(self):
        if not self._current:
            return
        old_id = self._current["id"]
        new_id, ok = QInputDialog.getText(
            self, "复制战区", "新战区 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.theaters:
            QMessageBox.warning(self, "错误", "战区已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_faction_theater(
            content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _rename_theater(self):
        if not self._current:
            return
        old_id = self._current["id"]
        new_id, ok = QInputDialog.getText(
            self, "重命名战区", "新战区 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if new_id.strip() in self.theaters:
            QMessageBox.warning(self, "错误", "战区已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_faction_theater(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _delete_theater(self):
        if not self._current:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除战区 '%s' 吗？" % self._current["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_faction_theater(content, self._current["id"])
        atomic_write_text(mod_fp, content)
        self._reload()

    # ---------- 保存 ----------
    def _save(self):
        if not self._current:
            return
        t = self._current
        rel = t.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 派系战区文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = replace_top_block_field(
            content, t["id"], "name", self.name_edit.text().strip(), quoted=True)
        content = replace_top_block_field(
            content, t["id"], "can_skip_first_region",
            self.skip_edit.text().strip())
        for field in LIST_FIELDS:
            content = replace_ai_region_list(
                content, t["id"], field, self._list_values(field))
        for field in ADVANCED_FIELDS:
            text = (self._advanced_blocks.get(field) or "").strip()
            if text:
                content = upsert_top_block_child(
                    content, t["id"], field, text)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        t["name"] = self.name_edit.text().strip()
        t["can_skip_first_region"] = self.skip_edit.text().strip()
        for field in LIST_FIELDS:
            t[field] = self._list_values(field)
        for field in ADVANCED_FIELDS:
            t[field] = self._advanced_blocks.get(field, "")
        msg = "已保存 AI 派系战区 %s" % t["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_ai_faction_theater_list(file_path=None, mod_path="", hoi4_path="",
                                 entity_id=None, parent=None):
    """按文件/实体打开 AI 派系战区编辑器（兼容旧入口名）。"""
    theaters = load_ai_faction_theaters(mod_path, hoi4_path)
    if file_path:
        norm = os.path.normpath(file_path).replace("\\", "/")
        theaters = {tid: t for tid, t in theaters.items()
                    if os.path.normpath(t.get("file", "")).replace("\\", "/") == norm}
    if not theaters:
        return False
    dlg = AiFactionTheaterEditorDialog(
        theaters, mod_path, hoi4_path, parent,
        initial_id=entity_id if entity_id in theaters else None)
    dlg.exec()
    return True

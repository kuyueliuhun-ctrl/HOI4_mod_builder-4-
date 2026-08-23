"""AI 科研权重专用编辑器（完全专用 UI，不依赖树形编辑器页面）

- 左侧固定侧边栏：权重块列表 + 搜索 + CRUD
- 主内容：research = { 科技 = 权重 } 键值表
- 原始块编辑通过 ScriptBlockEditorDialog 兜底
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QMenu, QMessageBox,
    QPushButton, QToolButton, QVBoxLayout,
)

from ai_loader import (
    _AI_CACHE,
    delete_ai_focus,
    duplicate_ai_focus,
    insert_ai_focus,
    load_ai_focuses,
    rename_ai_focus,
    replace_top_block_child,
)
from ai_ui_common import EntityListSidebar, KeyValueTableEditor, ScriptBlockEditorDialog
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text


class AiFocusEditorDialog(QDialog):
    """AI 科研权重专用编辑器。"""

    def __init__(self, focuses, mod_path="", hoi4_path="", parent=None,
                 initial_block_id=None):
        super().__init__(parent)
        self.focuses = focuses
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self._current = None
        self.setWindowTitle("AI 科研权重编辑器")
        self.resize(1000, 680)
        self.setMinimumSize(920, 600)
        self._build_ui()
        self._populate(initial_block_id)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = EntityListSidebar("科研权重块", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_block_changed)
        self.sidebar.createRequested.connect(self._create_block)
        self.sidebar.duplicateRequested.connect(self._duplicate_block)
        self.sidebar.renameRequested.connect(self._rename_block)
        self.sidebar.deleteRequested.connect(self._delete_block)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)

        right.addWidget(QLabel("research（科技 = 权重）"))
        self.table = KeyValueTableEditor("科技", "权重", self)
        right.addWidget(self.table, 1)

        raw_row = QHBoxLayout()
        advanced_btn = QToolButton()
        advanced_btn.setText("高级 ▾")
        advanced_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        raw_menu = QMenu(advanced_btn)
        raw_act = raw_menu.addAction("高级：原始 PDX（兜底）")
        raw_act.setToolTip("用高级块编辑器查看/编辑该块全部内容（含未知字段）")
        raw_act.triggered.connect(self._edit_raw)
        advanced_btn.setMenu(raw_menu)
        raw_row.addWidget(advanced_btn)
        raw_row.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        raw_row.addWidget(save_btn)
        right.addLayout(raw_row)
        root.addLayout(right, 1)

    def _populate(self, initial_block_id=None):
        items = [(bid, bid) for bid in sorted(self.focuses)]
        self.sidebar.set_entities(items)
        if initial_block_id:
            self.sidebar.set_current(initial_block_id)
        elif self.sidebar.current_id() is None and self.sidebar.list.count():
            self.sidebar.set_current(self.sidebar.list.item(0).data(
                Qt.ItemDataRole.UserRole))

    def _on_block_changed(self, block_id):
        if block_id is None:
            self._current = None
            self.id_label.setText("—")
            self.table.set_data({})
            return
        block = self.focuses.get(block_id)
        if not block:
            return
        self._current = block
        self.id_label.setText("%s  （%s）" % (block_id, block.get("file", "")))
        self.table.set_data(block.get("research", {}))

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
        _AI_CACHE.pop(("ai_focuses", self.mod_path or "",
                       self.hoi4_path or ""), None)
        self.focuses = load_ai_focuses(self.mod_path, self.hoi4_path)
        if self._current:
            norm = os.path.normpath(self._current.get("file", "")).replace("\\", "/")
            self.focuses = {bid: b for bid, b in self.focuses.items()
                            if os.path.normpath(b.get("file", "")).replace("\\", "/") == norm}
        self._populate(keep_id)

    def _create_block(self):
        if not self._current:
            return
        new_id, ok = QInputDialog.getText(self, "新建权重块", "块 ID：")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.focuses:
            QMessageBox.warning(self, "错误", "块已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = insert_ai_focus(content, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _duplicate_block(self):
        if not self._current:
            return
        old_id = self._current["id"]
        new_id, ok = QInputDialog.getText(
            self, "复制权重块", "新块 ID：", text=old_id + "_copy")
        if not ok or not new_id.strip():
            return
        if new_id.strip() in self.focuses:
            QMessageBox.warning(self, "错误", "块已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = duplicate_ai_focus(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _rename_block(self):
        if not self._current:
            return
        old_id = self._current["id"]
        new_id, ok = QInputDialog.getText(
            self, "重命名权重块", "新块 ID：", text=old_id)
        if not ok or not new_id.strip() or new_id.strip() == old_id:
            return
        if new_id.strip() in self.focuses:
            QMessageBox.warning(self, "错误", "块已存在：%s" % new_id)
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = rename_ai_focus(content, old_id, new_id.strip())
        atomic_write_text(mod_fp, content)
        self._reload(new_id.strip())

    def _delete_block(self):
        if not self._current:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除权重块 '%s' 吗？" % self._current["id"])
        if reply != QMessageBox.StandardButton.Yes:
            return
        mod_fp, _copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, self._current.get("rel", ""))
        if not mod_fp:
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        content = delete_ai_focus(content, self._current["id"])
        atomic_write_text(mod_fp, content)
        self._reload()

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
            title="AI 科研权重 - %s" % self._current["id"],
        )
        if dlg.exec():
            self._current["raw"] = dlg.get_block_text()

    # ---------- 保存 ----------
    def _save(self):
        if not self._current:
            return
        block = self._current
        rel = block.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(
            self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位 AI 科研权重文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        research = self.table.data()
        lines = ["research = {"]
        for tech, weight in research.items():
            lines.append("\t%s = %s" % (tech, weight))
        lines.append("}")
        content = replace_top_block_child(
            content, block["id"], "research", "\n".join(lines))
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        block["research"] = research
        msg = "已保存 AI 科研权重 %s" % block["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def open_ai_focus_editor(file_path, mod_path="", hoi4_path="",
                         entity_id=None, parent=None):
    """按文件/实体打开 AI 科研权重编辑器。"""
    focuses = load_ai_focuses(mod_path, hoi4_path)
    norm = os.path.normpath(file_path).replace("\\", "/")
    file_focuses = {}
    for bid, b in focuses.items():
        if os.path.normpath(b.get("file", "")).replace("\\", "/") == norm:
            file_focuses[bid] = b
    if not file_focuses:
        return False
    dlg = AiFocusEditorDialog(
        file_focuses, mod_path, hoi4_path, parent,
        initial_block_id=entity_id if entity_id in file_focuses else None)
    dlg.exec()
    return True

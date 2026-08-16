"""AI 派系战区列表对话框

- 列出全部 AI 派系战区
- 双击战区 → 打开通用树形编辑器并定位该战区
- 地图编辑器中的红色描边由 map_editor_dialog 负责
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from ai_loader import load_ai_faction_theaters
from state_build_ops import ensure_file_in_mod


class AiFactionTheaterListDialog(QDialog):
    """AI 派系战区列表。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.theaters = load_ai_faction_theaters(self.mod_path, self.hoi4_path)
        self.setWindowTitle("AI 派系战区")
        self.resize(520, 560)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel("双击战区打开树形编辑器"))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_theater)
        for tid in sorted(self.theaters):
            t = self.theaters[tid]
            label = tid
            if t.get("name"):
                label += "  (%s)" % t["name"]
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, tid)
            self.list.addItem(item)
        root.addWidget(self.list, 1)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)

    def _open_theater(self, item):
        tid = item.data(Qt.ItemDataRole.UserRole)
        theater = self.theaters.get(tid)
        if not theater:
            return
        fp = theater.get("file", "")
        if not fp:
            return
        mod_fp, copied = self._ensure_writable(fp)
        if not mod_fp:
            QMessageBox.warning(self, "无法编辑", "请先打开 mod 目录")
            return
        self._open_tree_for_file(mod_fp, tid)

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
            title="AI 派系战区 - %s" % entity_id,
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


def open_ai_faction_theater_list(mod_path="", hoi4_path="", parent=None):
    dlg = AiFactionTheaterListDialog(mod_path, hoi4_path, parent)
    dlg.exec()

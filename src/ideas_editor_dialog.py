"""民族精神（ideas）专用编辑器（P2 ②）。

基于 load_ideas_grouped（wrapper ideas → 分类块 → 理念块），按分类分组导航：
- 顶部分类下拉 + 侧栏该分类下理念列表（避免 1.4 万条平铺）
- 右侧原始脚本体编辑（块内文本），保存只替换该理念块、其余原样保留
- 新建 / 复制 / 改名 / 删除 均定位到当前分类
保存经 replace_nested_block_text / insert_into_category + 原子写。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ai_loader import _AI_CACHE, load_ideas_grouped
from ai_ui_common import EntityListSidebar, file_tooltip
from structure_view import StructureView
from nested_block_crud import (
    delete_nested_block,
    duplicate_nested_block,
    rename_nested_block,
)
from political_editor_data import (
    block_inner_text,
    insert_into_category,
    replace_nested_block_text,
)
from write_utils import atomic_write_text

_WRAPPER = "ideas"
_DEPTH = 2


def _shared_translator():
    try:
        from gui_translator import get_translator
        return get_translator()
    except Exception:
        return None


def _read(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


class IdeasEditorDialog(QDialog):
    """民族精神（理念）专用编辑器（按分类分组）。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None, initial_id=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("民族精神（理念）编辑器")
        self.resize(1040, 660)
        self.entities = {}
        self._category = ""
        self._current_id = None

        root = QHBoxLayout(self)

        # 左侧：分类下拉 + 实体列表
        left = QVBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        left.addWidget(self.category_combo)
        self.sidebar = EntityListSidebar("理念", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_current_changed)
        left.addWidget(self.sidebar, 1)
        root.addLayout(left)

        # 右侧：原始脚本体编辑
        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)
        hint = QLabel("编辑理念块内部文本（不含外层 key = { }）；保存只替换本块。")
        hint.setWordWrap(True)
        right.addWidget(hint)
        self.editor = StructureView(translator=_shared_translator())
        self.editor.set_compact(True)
        self.editor.setMinimumHeight(200)
        right.addWidget(self.editor, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        right.addLayout(btn_row)
        root.addLayout(right, 1)

        self._wire_sidebar()
        self._reload()
        if initial_id:
            self.sidebar.set_current(initial_id)

    # ---------- 数据 ----------

    def _reload(self, select_id=None):
        _AI_CACHE.clear()
        try:
            self.entities = dict(
                load_ideas_grouped(self.mod_path, self.hoi4_path))
        except Exception:
            self.entities = {}
        categories = sorted({v.get("parent_id", "")
                             for v in self.entities.values() if v.get("parent_id")})
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItems(categories)
        self.category_combo.blockSignals(False)
        if self._category in categories:
            self.category_combo.setCurrentText(self._category)
        elif categories:
            self.category_combo.setCurrentIndex(0)
        self._refresh_list()

    def _refresh_list(self):
        cat = self.category_combo.currentText()
        self._category = cat
        items = sorted(
            (eid for eid, ent in self.entities.items()
             if ent.get("parent_id") == cat),
            key=str.lower)
        self.sidebar.set_entities(
            [(eid, eid, file_tooltip(self.entities.get(eid), getattr(self, "mod_path", ""), getattr(self, "hoi4_path", ""))
              or eid) for eid in items])

    def _on_category_changed(self, _text):
        self._refresh_list()

    def _on_current_changed(self, eid):
        self._current_id = eid
        if not eid or eid not in self.entities:
            self.id_label.setText("—")
            self.editor.load_text("")
            return
        ent = self.entities[eid]
        self.id_label.setText("理念：%s（分类 %s）" % (eid, ent.get("parent_id", "")))
        self.editor.load_text(block_inner_text(ent["raw"]).strip("\n"))

    # ---------- CRUD ----------

    def _wire_sidebar(self):
        self.sidebar.createRequested.connect(self._on_create)
        self.sidebar.duplicateRequested.connect(self._on_duplicate)
        self.sidebar.renameRequested.connect(self._on_rename)
        self.sidebar.deleteRequested.connect(self._on_delete)

    def _entity_file(self, eid):
        ent = self.entities.get(eid)
        return ent["file"] if ent else ""

    def _write(self, fp, content):
        atomic_write_text(fp, content, encoding="utf-8")
        self._reload(self._current_id)

    def _on_create(self):
        eid, ok = QInputDialog.getText(self, "新建理念",
                                       "理念 id（分类 %s）：" % self._category)
        eid = (eid or "").strip()
        if not ok or not eid or not self._category:
            return
        fp = self._entity_file(self._current_id)
        if not fp:
            return
        content = _read(fp)
        block_text = "%s = {\n\t\n}\n" % eid
        content = insert_into_category(
            content, _WRAPPER, self._category, block_text, depth=_DEPTH)
        self._write(fp, content)
        self.sidebar.set_current(eid)

    def _on_duplicate(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "复制理念",
                                          "新 id（复制 %s）：" % cur)
        new_id = (new_id or "").strip()
        if not ok or not new_id:
            return
        fp = self._entity_file(cur)
        content = _read(fp)
        content = duplicate_nested_block(
            content, cur, new_id, parent_id=_WRAPPER, depth=_DEPTH)
        self._write(fp, content)
        self.sidebar.set_current(new_id)

    def _on_rename(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "重命名理念", "新 id：")
        new_id = (new_id or "").strip()
        if not ok or not new_id or new_id == cur:
            return
        fp = self._entity_file(cur)
        content = _read(fp)
        content = rename_nested_block(
            content, cur, new_id, parent_id=_WRAPPER, depth=_DEPTH)
        self._write(fp, content)

    def _on_delete(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        if QMessageBox.question(self, "确认", "删除理念 %s？" % cur) \
                != QMessageBox.StandardButton.Yes:
            return
        fp = self._entity_file(cur)
        content = _read(fp)
        content = delete_nested_block(
            content, cur, parent_id=_WRAPPER, depth=_DEPTH)
        self._write(fp, content)

    # ---------- 保存 ----------

    def _on_save(self):
        eid = self._current_id
        if not eid or eid not in self.entities:
            QMessageBox.information(self, "提示", "请先选择一个理念")
            return
        ent = self.entities[eid]
        fp = ent["file"]
        body = self.editor.to_pdx_text().strip("\n")
        new_block = "%s = {\n%s\n}\n" % (eid, body)
        content = _read(fp)
        content = replace_nested_block_text(
            content, eid, new_block, wrapper_key=_WRAPPER, depth=_DEPTH)
        try:
            atomic_write_text(fp, content, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "错误", "保存失败：%s" % e)
            return
        self._reload(eid)
        QMessageBox.information(self, "已保存", "理念 %s 已保存" % eid)


def open_ideas_editor(file_path="", mod_path="", hoi4_path="",
                      entity_id=None, parent=None):
    """入口：加载并显示民族精神（理念）专用编辑器（非模态）。"""
    dlg = IdeasEditorDialog(mod_path, hoi4_path,
                            parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
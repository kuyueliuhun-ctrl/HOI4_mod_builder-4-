"""意识形态专用编辑器（P2 ②）。

侧栏列出全部意识形态（load_ideologies_detail，wrapper ideologies → 各意识形态块）；
表单编辑 color / dynamic_faction_names / types / rules / modifiers / faction_modifiers
子块；其余标量字段与未知子块在保存时原样保留（只替换已知子块）。
保存经 replace_nested_block_text + atomic_write_text 原子写。
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ai_loader import _AI_CACHE, load_ideologies_detail
from ai_ui_common import EntityListSidebar
from nested_block_crud import (
    delete_nested_block,
    duplicate_nested_block,
    insert_nested_block,
    rename_nested_block,
)
from political_editor_data import (
    block_inner_text,
    child_block_span,
    join_list_block,
    list_items_from_block,
    replace_child_block,
    replace_nested_block_text,
)
from write_utils import atomic_write_text

_SUB_BLOCKS = ("types", "rules", "modifiers", "faction_modifiers")

_WRAPPER = "ideologies"


def _read(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _split_lines(edit):
    out = []
    for line in edit.toPlainText().splitlines():
        line = line.strip().strip('"').strip()
        if line:
            out.append(line)
    return out


class IdeologiesEditorDialog(QDialog):
    """意识形态专用编辑器。"""

    def __init__(self, mod_path="", hoi4_path="", parent=None, initial_id=None):
        super().__init__(parent)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle("意识形态编辑器")
        self.resize(1020, 640)
        self.entities = {}
        self._current_id = None

        root = QHBoxLayout(self)
        self.sidebar = EntityListSidebar("意识形态", self)
        self.sidebar.set_paths(self.mod_path, self.hoi4_path)
        self.sidebar.currentChanged.connect(self._on_current_changed)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("font-weight:bold; font-size:15px;")
        right.addWidget(self.id_label)

        right.addWidget(QLabel("颜色 color（R G B）"))
        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("0 0 255")
        right.addWidget(self.color_edit)

        right.addWidget(QLabel("派系名 dynamic_faction_names（每行一个）"))
        self.faction_edit = QPlainTextEdit()
        self.faction_edit.setFixedHeight(80)
        right.addWidget(self.faction_edit)

        self._sub_edits = {}
        for k in _SUB_BLOCKS:
            right.addWidget(QLabel("%s（块内原文，可编辑）" % k))
            edit = QPlainTextEdit()
            edit.setFixedHeight(100)
            right.addWidget(edit)
            self._sub_edits[k] = edit

        right.addStretch(1)
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
                load_ideologies_detail(self.mod_path, self.hoi4_path))
        except Exception:
            self.entities = {}
        self.sidebar.set_entities(
            [(eid, eid) for eid in sorted(self.entities)])
        if select_id:
            self.sidebar.set_current(select_id)

    def _on_current_changed(self, eid):
        self._current_id = eid
        if not eid or eid not in self.entities:
            self.id_label.setText("—")
            return
        raw = self.entities[eid]["raw"]
        self.id_label.setText("意识形态：%s" % eid)
        span = child_block_span(raw, "color")
        if span:
            self.color_edit.setText(
                block_inner_text(raw[span[2]:span[3]]).strip())
        else:
            self.color_edit.setText("")
        span = child_block_span(raw, "dynamic_faction_names")
        if span:
            self.faction_edit.setPlainText(
                "\n".join(list_items_from_block(raw[span[0]:span[1]])))
        else:
            self.faction_edit.setPlainText("")
        for k in _SUB_BLOCKS:
            span = child_block_span(raw, k)
            inner = block_inner_text(raw[span[2]:span[3]]) if span else ""
            self._sub_edits[k].setPlainText(inner.strip("\n"))

    # ---------- CRUD ----------

    def _wire_sidebar(self):
        self.sidebar.createRequested.connect(self._on_create)
        self.sidebar.duplicateRequested.connect(self._on_duplicate)
        self.sidebar.renameRequested.connect(self._on_rename)
        self.sidebar.deleteRequested.connect(self._on_delete)

    def _entity_file(self):
        for ent in self.entities.values():
            return ent["file"]
        return ""

    def _write(self, fp, content):
        atomic_write_text(fp, content, encoding="utf-8")
        self._reload(self._current_id)

    def _on_create(self):
        eid, ok = QInputDialog.getText(self, "新建意识形态", "意识形态 id：")
        eid = (eid or "").strip()
        if not ok or not eid:
            return
        fp = self._entity_file()
        if not fp:
            return
        content = _read(fp)
        block_text = "%s = {\n\t\n}\n" % eid
        content = insert_nested_block(
            content, eid, block_text, parent_id=_WRAPPER, depth=1)
        self._write(fp, content)
        self.sidebar.set_current(eid)

    def _on_duplicate(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "复制意识形态",
                                          "新 id（复制 %s）：" % cur)
        new_id = (new_id or "").strip()
        if not ok or not new_id:
            return
        fp = self.entities[cur]["file"]
        content = _read(fp)
        content = duplicate_nested_block(
            content, cur, new_id, parent_id=_WRAPPER, depth=1)
        self._write(fp, content)
        self.sidebar.set_current(new_id)

    def _on_rename(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "重命名意识形态",
                                          "新 id：")
        new_id = (new_id or "").strip()
        if not ok or not new_id or new_id == cur:
            return
        fp = self.entities[cur]["file"]
        content = _read(fp)
        content = rename_nested_block(
            content, cur, new_id, parent_id=_WRAPPER, depth=1)
        self._write(fp, content)

    def _on_delete(self):
        cur = self.sidebar.current_id()
        if not cur:
            return
        if QMessageBox.question(self, "确认", "删除意识形态 %s？" % cur) \
                != QMessageBox.StandardButton.Yes:
            return
        fp = self.entities[cur]["file"]
        content = _read(fp)
        content = delete_nested_block(
            content, cur, parent_id=_WRAPPER, depth=1)
        self._write(fp, content)

    # ---------- 保存 ----------

    def _on_save(self):
        eid = self._current_id
        if not eid or eid not in self.entities:
            QMessageBox.information(self, "提示", "请先选择一个意识形态")
            return
        ent = self.entities[eid]
        fp = ent["file"]
        raw = ent["raw"]
        color = self.color_edit.text().strip()
        new_raw = replace_child_block(raw, "color",
                                      " " + color if color else "")
        new_raw = replace_child_block(
            new_raw, "dynamic_faction_names",
            join_list_block(_split_lines(self.faction_edit)))
        for k in _SUB_BLOCKS:
            new_raw = replace_child_block(
                new_raw, k, self._sub_edits[k].toPlainText().strip("\n"))
        content = _read(fp)
        content = replace_nested_block_text(
            content, eid, new_raw, wrapper_key=_WRAPPER, depth=1)
        try:
            atomic_write_text(fp, content, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "错误", "保存失败：%s" % e)
            return
        self._reload(eid)
        QMessageBox.information(self, "已保存", "意识形态 %s 已保存" % eid)


def open_ideologies_editor(file_path="", mod_path="", hoi4_path="",
                           entity_id=None, parent=None):
    """入口：加载并显示意识形态专用编辑器（非模态）。"""
    dlg = IdeologiesEditorDialog(mod_path, hoi4_path,
                                 parent=parent, initial_id=entity_id)
    dlg.show()
    return dlg
"""通用顶层块动态编辑器（B3 铺开用）。

对「common/<目录>/*.txt 中每个顶层块 = 一组标量字段」的文件形态，
提供一个通用对话框：SimpleEntityTab 动态 text 表单 + replace_top_block_fields
写回。新类型只需提供 loader 函数 + 目录名 + 标题即可复用。

v2：接通侧栏 CRUD（创建/复制/改名/删除），全部走原子写 + 原版自动落 mod。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QInputDialog, QMessageBox, QVBoxLayout

from ai_loader import (
    _AI_CACHE,
    delete_top_block,
    duplicate_top_block,
    insert_top_block,
    rename_top_block,
    replace_top_block_fields,
)
from simple_entity_tab import SimpleEntityTab
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

SKIP_KEYS = {"id", "raw", "file", "rel", "parent_id"}


class SimpleBlockEditorDialog(QDialog):
    """通用顶层块编辑器。"""

    def __init__(self, loader, list_title, window_title, mod_path="",
                 hoi4_path="", parent=None, initial_id=None):
        super().__init__(parent)
        self.loader = loader
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle(window_title)
        self.resize(1080, 680)

        self._root = QVBoxLayout(self)
        self.tab = None
        self._build_tab()
        if initial_id:
            self.tab.sidebar.set_current(initial_id)

    # ---------- 构建 / 刷新 ----------

    def _build_tab(self):
        if self.tab is not None:
            old = self.tab
            self._root.removeWidget(old)
            old.deleteLater()
        self.entities = self._load_entities()
        all_keys = []
        for ent in self.entities.values():
            for k in ent:
                if k not in SKIP_KEYS and k not in all_keys:
                    all_keys.append(k)
        fields = [{"key": k, "label": k, "type": "text"} for k in all_keys]

        entities = []
        for eid, ent in self.entities.items():
            e = {"id": eid, "name": eid}
            for k in all_keys:
                e[k] = ent.get(k, "")
            e["rel"] = ent.get("rel", "")
            e["parent_id"] = ent.get("parent_id", "")
            entities.append(e)

        self.tab = SimpleEntityTab(entities, fields, self.mod_path,
                                   self.hoi4_path, parent=self,
                                   list_title=self._list_title())
        self.tab.saved.connect(self._on_save)
        self._wire_sidebar()
        self._root.addWidget(self.tab)

    def _load_entities(self):
        try:
            return dict(self.loader(self.mod_path, self.hoi4_path))
        except Exception:
            return {}

    def _list_title(self):
        return "实体"

    def _refresh(self, select_id=None):
        _AI_CACHE.clear()
        self._build_tab()
        if select_id:
            self.tab.sidebar.set_current(select_id)

    def _wire_sidebar(self):
        sb = self.tab.sidebar
        if sb.create_btn is None:
            return
        sb.createRequested.connect(self._on_create)
        sb.duplicateRequested.connect(self._on_duplicate)
        sb.renameRequested.connect(self._on_rename)
        sb.deleteRequested.connect(self._on_delete)

    # ---------- 文件读写 ----------

    def _current_rel(self):
        if self.tab._current is not None:
            rel = self.tab._current.get("rel", "")
            if rel:
                return rel
        for ent in self.entities.values():
            rel = ent.get("rel", "")
            if rel:
                return rel
        return ""

    def _read_mod_file(self, rel):
        """返回 (mod_fp, content, copied)。rel 空时返回 (None, "", False)。"""
        if not rel:
            return None, "", False
        mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            return None, "", False
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        return mod_fp, content, copied

    def _write_mod_file(self, mod_fp, content, msg=""):
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "写入失败", "写入失败：%s" % e)
            return False
        if msg:
            QMessageBox.information(self, "已保存", msg)
        return True

    # ---------- 保存（编辑字段） ----------

    def _on_save(self):
        if self.tab._current is None:
            return
        ent = self.tab._current
        rel = ent.get("rel", "")
        if not rel:
            return
        mod_fp, content, copied = self._read_mod_file(rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位文件")
            return
        values = self.tab.values()
        fields = {k: v for k, v in values.items() if v != ""}
        content = replace_top_block_fields(content, ent["id"], fields)
        if not self._write_mod_file(mod_fp, content):
            return
        for k, v in fields.items():
            ent[k] = v
        msg = "已保存 %s" % ent["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)

    # ---------- 侧栏 CRUD（顶层块） ----------

    def _on_create(self):
        new_id, ok = QInputDialog.getText(self, "新建实体", "新实体 id：")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()
        if new_id in self.entities:
            QMessageBox.warning(self, "新建失败", "id 已存在：%s" % new_id)
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            QMessageBox.warning(self, "新建失败", "无法定位目标文件")
            return
        after_id = self.tab.sidebar.current_id() or None
        content = insert_top_block(
            content, "\n%s = {\n}\n" % new_id, after_id=after_id)
        if not self._write_mod_file(mod_fp, content,
                                    "已创建 %s" % new_id):
            return
        self._refresh(select_id=new_id)

    def _on_duplicate(self):
        cur = self.tab.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "复制实体",
                                          "新实体 id：", text=cur + "_copy")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()
        if new_id in self.entities:
            QMessageBox.warning(self, "复制失败", "id 已存在：%s" % new_id)
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            return
        content = duplicate_top_block(content, cur, new_id)
        if not self._write_mod_file(mod_fp, content,
                                    "已复制为 %s" % new_id):
            return
        self._refresh(select_id=new_id)

    def _on_rename(self):
        cur = self.tab.sidebar.current_id()
        if not cur:
            return
        new_id, ok = QInputDialog.getText(self, "重命名实体",
                                          "新 id：", text=cur)
        if not ok or not new_id.strip() or new_id.strip() == cur:
            return
        new_id = new_id.strip()
        if new_id in self.entities:
            QMessageBox.warning(self, "重命名失败", "id 已存在：%s" % new_id)
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            return
        content = rename_top_block(content, cur, new_id)
        if not self._write_mod_file(mod_fp, content,
                                    "已重命名为 %s" % new_id):
            return
        self._refresh(select_id=new_id)

    def _on_delete(self):
        cur = self.tab.sidebar.current_id()
        if not cur:
            return
        ret = QMessageBox.question(
            self, "删除实体", "确定删除 %s ？" % cur,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        rel = self._current_rel()
        mod_fp, content, _copied = self._read_mod_file(rel)
        if not mod_fp:
            return
        content = delete_top_block(content, cur)
        if not self._write_mod_file(mod_fp, content,
                                    "已删除 %s" % cur):
            return
        self._refresh()


def make_simple_block_dialog(loader, list_title, window_title):
    """返回可被路由使用的对话框类（构造参数与 SimpleBlockEditorDialog 对齐）。"""

    class _Dialog(SimpleBlockEditorDialog):
        def __init__(self, mod_path="", hoi4_path="", parent=None,
                     initial_id=None):
            super().__init__(loader, list_title, window_title,
                             mod_path, hoi4_path, parent, initial_id)

    return _Dialog

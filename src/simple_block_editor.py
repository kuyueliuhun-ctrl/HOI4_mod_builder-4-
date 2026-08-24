"""通用顶层块动态编辑器（B3 铺开用）。

对「common/<目录>/*.txt 中每个顶层块 = 一组标量字段」的文件形态，
提供一个通用对话框：SimpleEntityTab 动态 text 表单 + replace_top_block_fields
写回。新类型只需提供 loader 函数 + 目录名 + 标题即可复用。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox, QVBoxLayout

from ai_loader import replace_top_block_fields
from simple_entity_tab import SimpleEntityTab
from state_build_ops import ensure_file_in_mod
from write_utils import atomic_write_text

SKIP_KEYS = {"id", "raw", "file", "rel"}


class SimpleBlockEditorDialog(QDialog):
    """通用顶层块编辑器。"""

    def __init__(self, loader, list_title, window_title, mod_path="",
                 hoi4_path="", parent=None, initial_id=None):
        super().__init__(parent)
        self.loader = loader
        self.entities = loader(mod_path, hoi4_path)
        self.mod_path = mod_path or ""
        self.hoi4_path = hoi4_path or ""
        self.setWindowTitle(window_title)
        self.resize(1080, 680)

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
            entities.append(e)

        root = QVBoxLayout(self)
        self.tab = SimpleEntityTab(entities, fields, self.mod_path,
                                   self.hoi4_path, parent=self,
                                   list_title=list_title)
        self.tab.saved.connect(self._on_save)
        root.addWidget(self.tab)
        if initial_id:
            self.tab.sidebar.set_current(initial_id)

    def _on_save(self):
        if self.tab._current is None:
            return
        ent = self.tab._current
        rel = ent.get("rel", "")
        if not rel:
            return
        mod_fp, copied = ensure_file_in_mod(self.mod_path, self.hoi4_path, rel)
        if not mod_fp:
            QMessageBox.warning(self, "保存失败", "无法定位文件")
            return
        with open(mod_fp, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        values = self.tab.values()
        fields = {k: v for k, v in values.items() if v != ""}
        content = replace_top_block_fields(content, ent["id"], fields)
        try:
            atomic_write_text(mod_fp, content)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "写入失败：%s" % e)
            return
        for k, v in fields.items():
            ent[k] = v
        msg = "已保存 %s" % ent["id"]
        if copied:
            msg += "\n原版文件已自动复制到 mod"
        QMessageBox.information(self, "已保存", msg)


def make_simple_block_dialog(loader, list_title, window_title):
    """返回可被路由使用的对话框类（构造参数与 SimpleBlockEditorDialog 对齐）。"""

    class _Dialog(SimpleBlockEditorDialog):
        def __init__(self, mod_path="", hoi4_path="", parent=None,
                     initial_id=None):
            super().__init__(loader, list_title, window_title,
                             mod_path, hoi4_path, parent, initial_id)

    return _Dialog